// Calcul des potions d'alchimie de Skyrim, entièrement dans le navigateur.
// Portage en JavaScript des scripts python/ (recipes.py, value.py, optimize.py) :
// les deux versions doivent donner les mêmes résultats.

// ---------------------------------------------------------------------------
// Données
// ---------------------------------------------------------------------------

async function loadData() {
  const [ingredients, effects] = await Promise.all([
    fetch("ingredients.json").then(r => r.json()),
    fetch("effects.json").then(r => r.json()),
  ]);
  return {
    ingredientsDb: Object.fromEntries(ingredients.map(i => [i.name, i])),
    effectsDb: Object.fromEntries(effects.map(e => [e.name, e])),
  };
}

function effectNames(ingredient) {
  return ingredient.effects.map(e => e.effect);
}

// ---------------------------------------------------------------------------
// Potions faisables (recipes.py)
// ---------------------------------------------------------------------------

// Renvoie les effets présents dans au moins 2 des ingrédients donnés.
function potionEffects(ingredients) {
  const counts = {};
  for (const ing of ingredients) {
    for (const name of effectNames(ing)) counts[name] = (counts[name] || 0) + 1;
  }
  return Object.keys(counts).filter(name => counts[name] >= 2).sort();
}

// Une recette est utile si chaque ingrédient est indispensable :
// le retirer doit faire perdre au moins un effet à la potion.
function isUseful(ingredients, effects) {
  if (effects.length === 0) return false;
  if (ingredients.length === 2) return true;
  for (let i = 0; i < ingredients.length; i++) {
    const others = ingredients.filter((_, j) => j !== i);
    if (potionEffects(others).length === effects.length) return false;
  }
  return true;
}

// Toutes les combinaisons de `size` éléments, dans l'ordre (comme itertools.combinations).
// Générateur : évite de garder en mémoire des centaines de milliers de combinaisons.
function* combinations(items, size, start = 0, prefix = []) {
  if (prefix.length === size) {
    yield prefix;
    return;
  }
  for (let i = start; i < items.length; i++) {
    yield* combinations(items, size, i + 1, [...prefix, items[i]]);
  }
}

// Renvoie la liste des recettes {ingredients: [noms], effects: [noms]} faisables.
function findRecipes(inventory, ingredientsDb) {
  const names = Object.keys(inventory).sort();
  const recipes = [];
  for (const size of [2, 3]) {
    for (const combo of combinations(names, size)) {
      const ingredients = combo.map(name => ingredientsDb[name]);
      const effects = potionEffects(ingredients);
      if (isUseful(ingredients, effects)) recipes.push({ ingredients: combo, effects });
    }
  }
  return recipes;
}

// ---------------------------------------------------------------------------
// Valeur des potions (value.py) — formules tirées de UESP
// ---------------------------------------------------------------------------

// Personnage de référence : Alchimie 15, sans perk ni équipement.
const DEFAULT_CHARACTER = {
  skill: 15,             // niveau d'Alchimie
  fortify_alchemy: 0,    // somme des enchantements Fortify Alchemy (en %)
  alchemist_rank: 0,     // perk Alchimiste : 0 à 5 (+20 % par rang)
  physician: false,      // +25 % sur Restore Health/Magicka/Stamina
  benefactor: false,     // +25 % sur les effets bénéfiques des potions
  poisoner: false,       // +25 % sur les effets nocifs des poisons
};

const PHYSICIAN_EFFECTS = new Set(["Restore Health", "Restore Magicka", "Restore Stamina"]);

// Ramène les valeurs saisies dans des bornes valides.
function normalizeCharacter(data) {
  const clamp = (x, min, max) => Math.min(Math.max(x, min), max);
  return {
    skill: clamp(Math.trunc(Number(data.skill) || 15), 15, 100),
    fortify_alchemy: Math.max(Number(data.fortify_alchemy) || 0, 0),
    alchemist_rank: clamp(Math.trunc(Number(data.alchemist_rank) || 0), 0, 5),
    physician: Boolean(data.physician),
    benefactor: Boolean(data.benefactor),
    poisoner: Boolean(data.poisoner),
  };
}

// Arrondi « au pair le plus proche », comme round() en Python.
function pyRound(x) {
  const r = Math.round(x);
  return Math.abs(x % 1) === 0.5 && r % 2 !== 0 ? r - 1 : r;
}

// Multiplicateur appliqué à la magnitude ou à la durée d'un effet.
function powerFactor(character, effect, isPoison) {
  const skillMult = 1 + 0.5 * character.skill / 100;
  let factor = 4 * skillMult;
  factor *= 1 + character.fortify_alchemy / 100;
  factor *= 1 + 0.2 * character.alchemist_rank;
  if (character.physician && PHYSICIAN_EFFECTS.has(effect.name)) factor *= 1.25;
  if (character.benefactor && !isPoison && !effect.harmful) factor *= 1.25;
  if (character.poisoner && isPoison && effect.harmful) factor *= 1.25;
  return factor;
}

// Renvoie le premier élément qui maximise key (comme max() en Python).
function maxBy(items, key) {
  let best = items[0];
  for (const item of items) if (key(item) > key(best)) best = item;
  return best;
}

// Version de l'effet issue de l'ingrédient le plus puissant (plus grand mag x dur).
function strongestIngredientEffect(effectName, ingredients) {
  const candidates = ingredients.flatMap(ing => ing.effects.filter(e => e.effect === effectName));
  return maxBy(candidates, e => e.mag * e.dur);
}

// Renvoie {mag, dur, gold} d'un effet dans une potion.
function effectValue(effect, ingEffect, character, isPoison) {
  const factor = powerFactor(character, effect, isPoison);
  let mag = effect.base_mag * ingEffect.mag;
  let dur = effect.base_dur * ingEffect.dur;
  if (effect.power_affects === "magnitude") mag *= factor;
  else dur *= factor;
  mag = pyRound(mag);
  dur = pyRound(dur);

  const magFactor = mag > 0 ? mag : 1;
  const durFactor = dur > 0 ? dur / 10 : 1;
  const gold = Math.floor(effect.base_cost * Math.pow(magFactor * durFactor, 1.1));
  return { mag, dur, gold };
}

// Ajoute à la recette son type (potion/poison), le détail des effets et sa valeur.
function evaluate(recipe, ingredientsDb, effectsDb, character = DEFAULT_CHARACTER) {
  const ingredients = recipe.ingredients.map(name => ingredientsDb[name]);
  const pairs = recipe.effects.map(name => [effectsDb[name], strongestIngredientEffect(name, ingredients)]);

  // L'effet le plus cher (hors perks Benefactor/Poisoner) décide si c'est un poison.
  const neutral = { ...character, benefactor: false, poisoner: false };
  const [mainEffect] = maxBy(pairs, ([effect, ingEffect]) => effectValue(effect, ingEffect, neutral, false).gold);
  const isPoison = mainEffect.harmful;

  const details = pairs.map(([effect, ingEffect]) => ({
    effect: effect.name,
    ...effectValue(effect, ingEffect, character, isPoison),
  }));
  details.sort((a, b) => b.gold - a.gold);

  return {
    ...recipe,
    type: isPoison ? "Poison" : "Potion",
    details,
    value: details.reduce((sum, d) => sum + d.gold, 0),
  };
}

// ---------------------------------------------------------------------------
// Optimisation (optimize.py) — programmation linéaire en nombres entiers
// ---------------------------------------------------------------------------

// Solveur HiGHS compilé en WebAssembly (le même que celui utilisé côté Python).
const HIGHS_URL = "https://cdn.jsdelivr.net/npm/highs@1.15.3/build/";
let highsPromise = null;

function loadHighs() {
  if (!highsPromise) highsPromise = Module({ locateFile: file => HIGHS_URL + file });
  return highsPromise;
}

// Renvoie la liste des [potion, nombre à fabriquer] qui maximise l'or total.
//
// Variables  : x[r] = nombre de fois qu'on fabrique la recette r (entier >= 0)
// Objectif   : maximiser la somme des valeur[r] * x[r]
// Contraintes: pour chaque ingrédient, quantité utilisée <= quantité possédée
function optimize(inventory, potions, highs) {
  potions = potions.filter(p => p.value > 0);
  if (potions.length === 0) return [];

  // Problème écrit au format LP (un terme par ligne pour éviter les lignes trop longues).
  const lines = ["Maximize", " obj:"];
  potions.forEach((p, r) => lines.push(`  + ${p.value} x${r}`));
  lines.push("Subject To");
  Object.entries(inventory).forEach(([name, qty], c) => {
    const used = potions.flatMap((p, r) => (p.ingredients.includes(name) ? [r] : []));
    if (used.length === 0) return;
    lines.push(` c${c}:`);
    used.forEach(r => lines.push(`  + x${r}`));
    lines.push(`  <= ${qty}`);
  });
  lines.push("General");
  potions.forEach((_, r) => lines.push(`  x${r}`));
  lines.push("End");

  const result = highs.solve(lines.join("\n"));
  if (result.Status !== "Optimal") throw new Error(`No optimal solution found: ${result.Status}`);

  const plan = potions
    .map((p, r) => [p, Math.round(result.Columns[`x${r}`].Primal)])
    .filter(([, count]) => count > 0);
  plan.sort((a, b) => b[0].value - a[0].value);
  return plan;
}

// Renvoie les ingrédients non utilisés par le plan.
function remainingInventory(inventory, plan) {
  const remaining = { ...inventory };
  for (const [potion, count] of plan) {
    for (const name of potion.ingredients) remaining[name] -= count;
  }
  return Object.fromEntries(Object.entries(remaining).filter(([, qty]) => qty > 0));
}

// Calcule le plan optimal pour l'inventaire et le personnage donnés.
function computePlan(inventory, characterData, data, highs) {
  inventory = Object.fromEntries(
    Object.entries(inventory)
      .map(([name, qty]) => [name, Math.trunc(Number(qty))])
      .filter(([name, qty]) => name in data.ingredientsDb && qty > 0)
  );
  const character = normalizeCharacter(characterData);

  const potions = findRecipes(inventory, data.ingredientsDb)
    .map(r => evaluate(r, data.ingredientsDb, data.effectsDb, character));
  const plan = optimize(inventory, potions, highs);

  return {
    plan: plan.map(([p, count]) => ({
      count, ingredients: p.ingredients, type: p.type, value: p.value, details: p.details,
    })),
    total: plan.reduce((sum, [p, count]) => sum + p.value * count, 0),
    remaining: remainingInventory(inventory, plan),
  };
}

// Permet aussi d'utiliser ce fichier depuis Node (tests).
if (typeof module !== "undefined") {
  module.exports = { findRecipes, evaluate, optimize, computePlan, DEFAULT_CHARACTER };
}
