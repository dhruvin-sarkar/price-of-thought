# Robustness to the edge threshold

## Hypothesis (stated before any statistic in this file was computed)

Every result so far uses edges carrying at least 1% of the target node's input. The graph is rebuilt at thresholds of 0.5%, 2% and 5%, with node positions and compartments unchanged, and three headline tests are repeated at each with the procedures and seeds of the original analyses:

1. Placement (`results/spatial_optimality.md`, primary): total unweighted wiring cost against 1000 permutations of node positions.
2. Rich-to-rich routing through the connective (`results/connective_richclub.md`, H1): total routes R at the top-10% richness threshold against 1000 layer-preserving rewirings.
3. Connective hubs (`results/connective_richclub.md`, H3): odds ratio of descending and ascending nodes among nodes with total degree at or above the 90th percentile, Fisher exact test.

> **H11**: at every threshold each test keeps the direction and the significance (α = 0.05) it had at 1%: real cost below every permutation, real R above the rewired null, odds ratio above 1.

The number of nodes, edges and connective layer sizes at each threshold is reported alongside. A threshold at which a result fails is reported as such.
