# Skyrim Alchemy Calculator

> _"Fancy yourself an alchemist, hmm? Never could get the hang of that"_

You've just come back from a long trip with a bag full of ingredients, and you'd like to turn them into as much gold as possible. Which potions should you brew, and how many of each?

This little tool answers that question.

https://ceciestunpseudooo.github.io/alchemy-calculator/

## How to use it

1. Set up your character: Alchemy skill, Fortify Alchemy gear, and the perks you have.
2. Add the ingredients you own, with their quantities.
3. Click **Find the best potions**.

You get a list of potions to brew, how many times to brew each one, the total gold you'll earn, and the ingredients you'll have left over.

## How we built it

We went step by step, keeping things as simple as possible at each stage.

**1. The data.** Two JSON files describe the game: `ingredients.json` (171 ingredients from the base game, the DLCs and the Creation Club, each with its 4 effects) and `effects.json` (the 59 alchemy effects and their base stats).

**2. Which potions can I make?** In Skyrim, a potion uses 2 or 3 different ingredients, and it gets every effect shared by at least two of them. We try every combination of ingredients you own and keep the ones that produce at least one effect. When you use 3 ingredients, each one has to bring something: if removing one doesn't change the potion, the recipe is dropped.

**3. How much is it worth?** Each effect's price depends on its magnitude and duration, which grow with your skill, your gear and your perks. We used the formulas documented on [UESP](https://en.uesp.net/wiki/Skyrim:Alchemy). The potion's value is the sum of its effects' prices. Its most valuable effect decides whether it's a potion or a poison, which matters for the Benefactor and Poisoner perks.

**4. What's the best sequence of potions to brew?** This is the interesting part, so it gets [its own section below](#finding-the-best-plan).

## Finding the best plan

### Why the obvious approach fails

The natural idea is to be greedy: brew the most expensive potion you can, remove its ingredients from your bag, and repeat. It's fast, but it can miss the best answer.

Say you own one each of four ingredients A, B, C and D, and these recipes are possible:

| Recipe | Value    |
| ------ | -------- |
| A + B  | 100 gold |
| A + C  | 70 gold  |
| B + D  | 70 gold  |

The greedy approach brews A + B for 100 gold, and then C and D can't make anything together. Brewing A + C and B + D instead earns 140 gold. The expensive potion used up two ingredients that were worth more apart.

So instead of choosing one potion at a time, we look at all possible choices at once and solve an optimization problem.

### Linear Optimization problem

We write:

- $I$: the ingredients in your inventory, and $q_i$ the quantity you own of ingredient $i$;
- $R$: the recipes you can make (from step 2), and $v_r$ the value in gold of recipe $r$ (from step 3);
- $a_{i,r}$: equals $1$ if recipe $r$ uses ingredient $i$, and $0$ otherwise.

The unknowns are $x_r$: **how many times we brew recipe $r$**. The problem is then:

```math
\begin{aligned}
\text{maximize} \quad & \sum_{r \in R} v_r \, x_r && \text{(total gold earned)} \\
\text{subject to} \quad & \sum_{r \in R} a_{i,r} \, x_r \le q_i && \text{for each ingredient } i \in I \\
& x_r \in \{0, 1, 2, \dots\} && \text{for each recipe } r \in R
\end{aligned}
```

In plain words:

- **The objective** adds up the gold of every potion we brew.
- **The constraints** say that for each ingredient, the recipes using it can't take more than we own. Each recipe uses one unit of each of its ingredients, so brewing it $x_r$ times uses $x_r$ units of each.
- **The last line** says we brew whole potions: you can't brew half a potion.

On the example above, with $x_{AB}$, $x_{AC}$ and $x_{BD}$, this gives: maximize $100 x_{AB} + 70 x_{AC} + 70 x_{BD}$, with $x_{AB} + x_{AC} \le 1$ (one A), $x_{AB} + x_{BD} \le 1$ (one B), $x_{AC} \le 1$ (one C) and $x_{BD} \le 1$ (one D). The best solution is $x_{AC} = x_{BD} = 1$ and $x_{AB} = 0$, for 140 gold.

Problems like this could take a lot of computation. But at our scale (a few hundred to a few thousand recipes for a normal inventory), a solver handles them in a fraction of a second. We use [HiGHS](https://highs.dev), an open-source solver that finds the optimal solution to the optimization problem (Thx Mr.Meunier <3). It's the same solver in both versions: through the `pulp` library in [`python/optimize.py`](python/optimize.py), and compiled for the browser in [`alchemy.js`](alchemy.js).

## Project layout

```
index.html, alchemy.js           the web page and its calculations
ingredients.json, effects.json   game data, shared by both versions
python/                          the original Python scripts
```

## Using the Python scripts

The Python version is still here if you prefer the command line. Put your ingredients in `python/inventory.json`, then:

```bash
pip install -r python/requirements.txt
cd python
python recipes.py    # list the potions you can make
python value.py      # same, with their value
python optimize.py   # the best brewing plan
```

To test the web page on your computer, run `python python/server.py` and open http://localhost:8000.

## Limitations

- Prices are calculated, not read from the game, so a few may be off by a little.
- With a huge inventory (all 171 ingredients at once), the optimization can take about a minute. With a normal inventory, it's instant.
