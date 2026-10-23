"""Choix des potions à fabriquer pour maximiser l'or gagné (programmation linéaire en nombres entiers)."""

import pulp

from data import load_effects, load_ingredients, load_inventory
from recipes import find_recipes
from value import DEFAULT_CHARACTER, evaluate


def optimize(inventory, potions):
    """Renvoie la liste des (potion, nombre à fabriquer) qui maximise l'or total.

    Variables  : x[r] = nombre de fois qu'on fabrique la recette r (entier >= 0)
    Objectif   : maximiser la somme des valeur[r] * x[r]
    Contraintes: pour chaque ingrédient, quantité utilisée <= quantité possédée
    """
    potions = [p for p in potions if p["value"] > 0]

    problem = pulp.LpProblem("alchimie", pulp.LpMaximize)
    x = [problem.add_variable(f"x{r}", lowBound=0, cat="Integer") for r in range(len(potions))]

    problem += pulp.lpSum(p["value"] * x[r] for r, p in enumerate(potions))

    for name, qty in inventory.items():
        used = [x[r] for r, p in enumerate(potions) if name in p["ingredients"]]
        if used:
            problem += pulp.lpSum(used) <= qty, name

    result = problem.solve(pulp.HiGHS(msg=False))
    if result.status != pulp.LpSolveStatus.Optimal:
        raise RuntimeError(f"Pas de solution optimale : {result.status.name}")

    plan = [(p, round(x[r].value())) for r, p in enumerate(potions) if x[r].value() > 0.5]
    plan.sort(key=lambda item: item[0]["value"], reverse=True)
    return plan


def remaining_inventory(inventory, plan):
    """Renvoie les ingrédients non utilisés par le plan."""
    remaining = dict(inventory)
    for potion, count in plan:
        for name in potion["ingredients"]:
            remaining[name] -= count
    return {name: qty for name, qty in remaining.items() if qty > 0}


if __name__ == "__main__":
    ingredients_db = load_ingredients()
    effects_db = load_effects()
    inventory = load_inventory()

    potions = [
        evaluate(r, ingredients_db, effects_db, DEFAULT_CHARACTER)
        for r in find_recipes(inventory, ingredients_db)
    ]
    plan = optimize(inventory, potions)

    total = 0
    print("Potions à fabriquer :\n")
    for p, count in plan:
        total += p["value"] * count
        print(f"{count:>3} x {p['value']:>5} or  {p['type']:<6}  " + " + ".join(p["ingredients"]))
    print(f"\nTotal : {total} or")

    remaining = remaining_inventory(inventory, plan)
    if remaining:
        print("\nIngrédients restants :")
        for name, qty in remaining.items():
            print(f"  {qty:>3} x {name}")
