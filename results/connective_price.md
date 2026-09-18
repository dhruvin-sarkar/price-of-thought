# Price and value of individual connective cell types

## Hypothesis (stated before any statistic in this file was computed)

**Units.** Every connective node c (a descending or ascending cell type on one side) with at least one neck-crossing edge (`results/connective_value.md`): DN → V and V → DN edges for a descending node, AN → B and B → AN edges for an ascending node.

**Price.** The summed Euclidean length of c's neck-crossing edges.

**Value.** The loss of flow capacity when c's neck-crossing edges alone are removed from the intact graph, in the direction the node carries: brain sensory to nerve-cord motor flow for a descending node, nerve-cord sensory to brain motor flow for an ascending node. The loss of whole-CNS sensory-to-motor flow is recorded as well. Metrics and sets are those of `results/connective_value.md`.

> **H10**: across connective nodes, price and value are **positively** correlated (Spearman, one-sided, α = 0.05), tested separately for descending and ascending nodes; supported if both are significant.

> **H10b**: the correlation survives control for the number of neck-crossing edges: the partial Spearman correlation of price and value given edge count (Pearson correlation of rank residuals after linear regression of each rank on the rank of edge count) is **positive** (one-sided, α = 0.05), separately for descending and ascending nodes; supported if both are significant. H10 alone could follow from nodes with more edges being both costlier and more valuable; H10b asks whether, at a given number of connections, longer wiring buys more flow.

Reported descriptively: the fraction of nodes whose removal costs no flow, the most valuable and the most expensive cell types, and value per millimetre of wire.

A result against either hypothesis is reported as such.

## Results

Hypotheses committed in `73fba33` before any statistic in this file was computed. Intact flow capacity: 6,423 brain sensory to nerve-cord motor, 2,228 nerve-cord sensory to brain motor.

| nodes | n | no flow lost | Spearman ρ (price, value) | p | partial ρ given edge count | p | ρ (edge count, value) |
|---|---|---|---|---|---|---|---|
| descending | 911 | 622 | 0.231 | 7.62e-13 | 0.044 | 0.0923 | 0.227 |
| ascending | 1,010 | 899 | -0.005 | 0.557 | -0.122 | 1 | 0.027 |

**H10 is not supported. H10b is not supported.**

Removing the neck-crossing edges of a single cell type usually costs no flow at all (622 of 911 descending and 899 of 1,010 ascending nodes): the remaining wiring supports the same maximum flow. Among descending nodes, price and value rise together only because both rise with the number of connections (ρ between edge count and value 0.23); at a fixed number of connections, longer wiring buys no more flow. Among ascending nodes price and value are unrelated, and the most expensive ascending types carry no nerve-cord-to-brain sensory-to-motor flow of their own.

### Descending cell types with the largest value

| node | edges | price | value | value per mm |
|---|---|---|---|---|
| DNpe036|R | 41 | 31.3 mm | 17 | 0.54 |
| DNpe034|L | 25 | 20.7 mm | 17 | 0.82 |
| DNg98|L | 172 | 114.6 mm | 16 | 0.14 |
| DNg98|R | 177 | 122.8 mm | 16 | 0.13 |
| DNg102|L | 101 | 65.9 mm | 15 | 0.23 |
| DNpe034|R | 22 | 17.8 mm | 15 | 0.84 |
| DNpe036|L | 46 | 34.9 mm | 14 | 0.40 |
| DNge002|L | 14 | 5.5 mm | 14 | 2.54 |
| DNge002|R | 14 | 5.5 mm | 14 | 2.55 |
| DNp58|L | 27 | 20.9 mm | 14 | 0.67 |
| DNp48|R | 51 | 37.0 mm | 13 | 0.35 |
| DNg102|R | 99 | 67.1 mm | 13 | 0.19 |
| DNge172|L | 35 | 27.8 mm | 13 | 0.47 |
| DNg70|R | 69 | 49.0 mm | 12 | 0.24 |
| DNp13|R | 68 | 44.4 mm | 12 | 0.27 |

### Descending cell types with the largest price

| node | edges | price | value | value per mm |
|---|---|---|---|---|
| DNg98|R | 177 | 122.8 mm | 16 | 0.13 |
| DNg98|L | 172 | 114.6 mm | 16 | 0.14 |
| DNae009|L | 93 | 68.8 mm | 0 | 0.00 |
| DNae009|R | 93 | 67.7 mm | 0 | 0.00 |
| DNg102|R | 99 | 67.1 mm | 13 | 0.19 |
| DNg102|L | 101 | 65.9 mm | 15 | 0.23 |
| DNge172|R | 74 | 56.2 mm | 10 | 0.18 |
| DNg08|L | 88 | 55.5 mm | 0 | 0.00 |
| DNge136|L | 75 | 54.2 mm | 11 | 0.20 |
| DNg08|R | 82 | 53.3 mm | 0 | 0.00 |
| DNge136|R | 73 | 51.1 mm | 9 | 0.18 |
| DNg100|L | 84 | 50.2 mm | 1 | 0.02 |
| aSP22|R | 68 | 49.8 mm | 1 | 0.02 |
| DNg70|R | 69 | 49.0 mm | 12 | 0.24 |
| DNd03|L | 75 | 48.8 mm | 1 | 0.02 |

### Ascending cell types with the largest value

| node | edges | price | value | value per mm |
|---|---|---|---|---|
| AN19B025|R | 28 | 15.2 mm | 9 | 0.59 |
| ANXXX071|R | 28 | 21.9 mm | 8 | 0.37 |
| ANXXX191|R | 12 | 5.6 mm | 7 | 1.25 |
| AN07B042|R | 16 | 5.7 mm | 7 | 1.22 |
| ANXXX071|L | 27 | 5.8 mm | 6 | 1.04 |
| AN19B025|L | 25 | 14.0 mm | 6 | 0.43 |
| AN10B009|L | 26 | 15.3 mm | 5 | 0.33 |
| ANXXX191|L | 8 | 3.9 mm | 5 | 1.29 |
| AN19B014|R | 11 | 6.0 mm | 5 | 0.83 |
| AN19B001|R | 24 | 13.0 mm | 4 | 0.31 |
| AN07B049|R | 19 | 6.1 mm | 4 | 0.65 |
| AN03A002|L | 11 | 5.1 mm | 4 | 0.78 |
| AN07B052|R | 19 | 6.8 mm | 4 | 0.59 |
| AN03A002|R | 7 | 3.1 mm | 4 | 1.27 |
| AN10B009|R | 18 | 10.1 mm | 4 | 0.40 |

### Ascending cell types with the largest price

| node | edges | price | value | value per mm |
|---|---|---|---|---|
| AN07B004|R | 316 | 146.2 mm | 2 | 0.01 |
| AN07B004|L | 313 | 137.4 mm | 2 | 0.01 |
| AN09B004|L | 123 | 103.9 mm | 0 | 0.00 |
| AN06B009|R | 184 | 98.9 mm | 0 | 0.00 |
| ANXXX027|L | 112 | 95.9 mm | 0 | 0.00 |
| AN06B009|L | 176 | 95.7 mm | 0 | 0.00 |
| ANXXX027|R | 114 | 94.6 mm | 0 | 0.00 |
| AN00A006|M | 110 | 92.0 mm | 0 | 0.00 |
| AN09B004|R | 110 | 91.0 mm | 0 | 0.00 |
| AN08B018|L | 135 | 86.5 mm | 0 | 0.00 |
| AN05B101|L | 147 | 85.8 mm | 0 | 0.00 |
| AN05B101|R | 146 | 85.4 mm | 0 | 0.00 |
| AN02A002|R | 149 | 84.1 mm | 0 | 0.00 |
| AN08B018|R | 128 | 81.6 mm | 0 | 0.00 |
| AN02A002|L | 129 | 74.3 mm | 0 | 0.00 |

Values are units of flow capacity lost; every node's figures are in `connective_price.csv`.

![Connective price and value](connective_price.png)
