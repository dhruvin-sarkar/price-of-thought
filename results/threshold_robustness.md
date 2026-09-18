# Robustness to the edge threshold

## Hypothesis (stated before any statistic in this file was computed)

Every result so far uses edges carrying at least 1% of the target node's input. The graph is rebuilt at thresholds of 0.5%, 2% and 5%, with node positions and compartments unchanged, and three headline tests are repeated at each with the procedures and seeds of the original analyses:

1. Placement (`results/spatial_optimality.md`, primary): total unweighted wiring cost against 1000 permutations of node positions.
2. Rich-to-rich routing through the connective (`results/connective_richclub.md`, H1): total routes R at the top-10% richness threshold against 1000 layer-preserving rewirings.
3. Connective hubs (`results/connective_richclub.md`, H3): odds ratio of descending and ascending nodes among nodes with total degree at or above the 90th percentile, Fisher exact test.

> **H11**: at every threshold each test keeps the direction and the significance (α = 0.05) it had at 1%: real cost below every permutation, real R above the rewired null, odds ratio above 1.

The number of nodes, edges and connective layer sizes at each threshold is reported alongside. A threshold at which a result fails is reported as such.

## Results

Hypotheses committed in `73fba33` before any statistic in this file was computed. The 1% row is recomputed by this script and should match the original analyses.

| threshold | nodes | edges | D_in | D_out | A_in | A_out |
|---|---|---|---|---|---|---|
| 0.5% | 23,073 | 942,400 | 26,845 | 33,561 | 24,081 | 30,464 |
| 1% (original) | 23,073 | 490,884 | 13,270 | 17,628 | 12,357 | 16,677 |
| 2% | 23,073 | 216,862 | 5,268 | 7,578 | 5,447 | 7,738 |
| 5% | 23,073 | 52,217 | 957 | 1,502 | 1,368 | 1,871 |

### Placement

| threshold | real / permuted cost | z | permutations at or below real | p |
|---|---|---|---|---|
| 0.5% | 0.460 | -323.2 | 0 of 1000 | 0.0010 |
| 1% (original) | 0.459 | -278.8 | 0 of 1000 | 0.0010 |
| 2% | 0.455 | -211.4 | 0 of 1000 | 0.0010 |
| 5% | 0.439 | -124.7 | 0 of 1000 | 0.0010 |

### Rich-to-rich routes, top 10%

| threshold | real routes | real / randomized | z | p | descending ratio (p) | ascending ratio (p) |
|---|---|---|---|---|---|---|
| 0.5% | 23,106 | 1.002 | 0.2 | 0.4246 | 1.042 (0.0090) | 0.979 (0.8851) |
| 1% (original) | 7,454 | 1.103 | 4.8 | 0.0010 | 0.984 (0.7093) | 1.150 (0.0010) |
| 2% | 2,317 | 1.391 | 11.0 | 0.0010 | 0.857 (0.9880) | 1.533 (0.0010) |
| 5% | 308 | 1.605 | 6.8 | 0.0010 | 1.311 (0.0420) | 1.725 (0.0010) |

### Connective hubs

| threshold | degree at 90th percentile | connective nodes above | other nodes above | odds ratio | p |
|---|---|---|---|---|---|
| 0.5% | 123 | 27.2% | 8.6% | 3.99 | 1.26e-117 |
| 1% (original) | 67 | 23.7% | 8.8% | 3.22 | 1.48e-79 |
| 2% | 32 | 19.1% | 9.6% | 2.22 | 4.77e-35 |
| 5% | 9 | 15.1% | 11.8% | 1.33 | 1.03e-05 |

The rich-to-rich route ratio changes with the threshold (1.00 at 0.5%, 1.10 at 1%, 1.39 at 2%, 1.61 at 5%): the enrichment is carried by the strongest connections and disappears when weak ones are added.

**H11 is not supported.** Results that do not hold: routes at 0.5%.
