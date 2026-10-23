"""Calcul de la valeur (en or) des potions.

Formules tirées de UESP (Skyrim:Alchemy et Skyrim:Alchemy_Effects).
"""

import math

from data import load_effects, load_ingredients, load_inventory
from recipes import find_recipes

# Personnage de référence : Alchimie 15, sans perk ni équipement.
DEFAULT_CHARACTER = {
    "skill": 15,            # niveau d'Alchimie
    "fortify_alchemy": 0,   # somme des enchantements Fortify Alchemy (en %)
    "alchemist_rank": 0,    # perk Alchimiste : 0 à 5 (+20 % par rang)
    "physician": False,     # +25 % sur Restore Health/Magicka/Stamina
    "benefactor": False,    # +25 % sur les effets bénéfiques des potions
    "poisoner": False,      # +25 % sur les effets nocifs des poisons
}

PHYSICIAN_EFFECTS = {"Restore Health", "Restore Magicka", "Restore Stamina"}


def power_factor(character, effect, is_poison):
    """Multiplicateur appliqué à la magnitude ou à la durée d'un effet."""
    skill_mult = 1 + 0.5 * character["skill"] / 100
    factor = 4 * skill_mult
    factor *= 1 + character["fortify_alchemy"] / 100
    factor *= 1 + 0.2 * character["alchemist_rank"]
    if character["physician"] and effect["name"] in PHYSICIAN_EFFECTS:
        factor *= 1.25
    if character["benefactor"] and not is_poison and not effect["harmful"]:
        factor *= 1.25
    if character["poisoner"] and is_poison and effect["harmful"]:
        factor *= 1.25
    return factor


def strongest_ingredient_effect(effect_name, ingredients):
    """Version de l'effet issue de l'ingrédient le plus puissant.

    Le jeu utilise l'ingrédient « prioritaire » (selon son prix interne, absent
    de nos données) ; on l'approche en prenant le plus grand mag x dur
    (le champ "val" n'est pas utilisé car il manque pour certains ingrédients).
    """
    candidates = [
        e for ing in ingredients for e in ing["effects"] if e["effect"] == effect_name
    ]
    return max(candidates, key=lambda e: e["mag"] * e["dur"])


def effect_value(effect, ing_effect, character, is_poison):
    """Renvoie (magnitude, durée, prix en or) d'un effet dans une potion."""
    factor = power_factor(character, effect, is_poison)
    mag = effect["base_mag"] * ing_effect["mag"]
    dur = effect["base_dur"] * ing_effect["dur"]
    if effect["power_affects"] == "magnitude":
        mag *= factor
    else:
        dur *= factor
    mag, dur = round(mag), round(dur)

    mag_factor = mag if mag > 0 else 1
    dur_factor = dur / 10 if dur > 0 else 1
    gold = math.floor(effect["base_cost"] * (mag_factor * dur_factor) ** 1.1)
    return mag, dur, gold


def evaluate(recipe, ingredients_db, effects_db, character=DEFAULT_CHARACTER):
    """Ajoute à la recette son type (potion/poison), le détail des effets et sa valeur."""
    ingredients = [ingredients_db[name] for name in recipe["ingredients"]]
    pairs = [
        (effects_db[name], strongest_ingredient_effect(name, ingredients))
        for name in recipe["effects"]
    ]

    # L'effet le plus cher (hors perks Benefactor/Poisoner) décide si c'est un poison.
    neutral = {**character, "benefactor": False, "poisoner": False}
    main_effect, _ = max(pairs, key=lambda p: effect_value(*p, neutral, False)[2])
    is_poison = main_effect["harmful"]

    details = []
    for effect, ing_effect in pairs:
        mag, dur, gold = effect_value(effect, ing_effect, character, is_poison)
        details.append({"effect": effect["name"], "mag": mag, "dur": dur, "gold": gold})
    details.sort(key=lambda d: d["gold"], reverse=True)

    return {
        **recipe,
        "type": "Poison" if is_poison else "Potion",
        "details": details,
        "value": sum(d["gold"] for d in details),
    }


if __name__ == "__main__":
    ingredients_db = load_ingredients()
    effects_db = load_effects()
    inventory = load_inventory()

    potions = [
        evaluate(r, ingredients_db, effects_db)
        for r in find_recipes(inventory, ingredients_db)
    ]
    potions.sort(key=lambda p: p["value"], reverse=True)

    for p in potions:
        print(f"{p['value']:>5} or  {p['type']:<6}  " + " + ".join(p["ingredients"]))
        for d in p["details"]:
            print(f"{'':>20}{d['effect']:<25} mag {d['mag']:>3}  dur {d['dur']:>3}s  {d['gold']:>4} or")
