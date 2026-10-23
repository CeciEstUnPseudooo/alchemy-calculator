"""Recherche des potions faisables à partir d'un inventaire."""

from collections import Counter
from itertools import combinations

from data import effect_names, load_ingredients, load_inventory


def potion_effects(ingredients):
    """Renvoie les effets présents dans au moins 2 des ingrédients donnés."""
    counts = Counter(name for ing in ingredients for name in effect_names(ing))
    return {name for name, n in counts.items() if n >= 2}


def is_useful(ingredients, effects):
    """Une recette est utile si chaque ingrédient est indispensable :
    le retirer doit faire perdre au moins un effet à la potion."""
    if not effects:
        return False
    if len(ingredients) == 2:
        return True
    for i in range(len(ingredients)):
        others = ingredients[:i] + ingredients[i + 1:]
        if potion_effects(others) == effects:
            return False
    return True


def find_recipes(inventory, ingredients_db):
    """Renvoie la liste des recettes faisables avec l'inventaire.

    Chaque recette est un dict {"ingredients": [noms], "effects": [noms]}.
    """
    names = sorted(inventory)
    recipes = []
    for size in (2, 3):
        for combo in combinations(names, size):
            ingredients = [ingredients_db[name] for name in combo]
            effects = potion_effects(ingredients)
            if is_useful(ingredients, effects):
                recipes.append({"ingredients": list(combo), "effects": sorted(effects)})
    return recipes


if __name__ == "__main__":
    ingredients_db = load_ingredients()
    inventory = load_inventory()
    recipes = find_recipes(inventory, ingredients_db)

    print(f"{len(recipes)} potions faisables :\n")
    for r in recipes:
        print(" + ".join(r["ingredients"]))
        print("    -> " + ", ".join(r["effects"]))
