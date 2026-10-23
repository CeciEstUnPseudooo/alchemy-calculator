"""Chargement des données d'alchimie de Skyrim."""

import json
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
DATA_DIR = SCRIPTS_DIR.parent  # les JSON du jeu sont partagés avec la page web


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_effects():
    """Renvoie un dict : nom de l'effet -> données de l'effet."""
    return {e["name"]: e for e in load_json(DATA_DIR / "effects.json")}


def load_ingredients():
    """Renvoie un dict : nom de l'ingrédient -> données de l'ingrédient."""
    return {i["name"]: i for i in load_json(DATA_DIR / "ingredients.json")}


def load_inventory(filename="inventory.json"):
    """Renvoie un dict : nom de l'ingrédient -> quantité possédée."""
    inventory = load_json(SCRIPTS_DIR / filename)
    ingredients = load_ingredients()
    unknown = [name for name in inventory if name not in ingredients]
    if unknown:
        raise ValueError(f"Ingrédients inconnus dans l'inventaire : {unknown}")
    return {name: qty for name, qty in inventory.items() if qty > 0}


def effect_names(ingredient):
    """Renvoie l'ensemble des noms d'effets d'un ingrédient."""
    return {e["effect"] for e in ingredient["effects"]}


if __name__ == "__main__":
    effects = load_effects()
    ingredients = load_ingredients()
    print(f"{len(ingredients)} ingrédients, {len(effects)} effets chargés.\n")

    name = "Blue Mountain Flower"
    print(f"Effets de {name} :")
    for e in ingredients[name]["effects"]:
        print(f"  - {e['effect']} (mag x{e['mag']}, dur x{e['dur']})")

    print("\nInventaire :")
    for name, qty in load_inventory().items():
        print(f"  {qty:>3} x {name}")
