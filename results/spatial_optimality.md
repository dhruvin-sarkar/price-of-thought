# Spatial optimality of cell-type placement

## Hypothesis (stated before any wiring cost was computed)

This section was committed before the spatial graph existed on disk; no position, edge length, or wiring cost had been computed when it was written.

**Graph.** Nodes are (cell type, hemisphere) pairs of the male CNS connectome (`male-cns:v1.0`). A directed edge joins two nodes when the connection supplies at least 1% of the target node's input synapses; self-loops are excluded. Each node sits at the centroid of its neurons' soma positions when at least half of its neurons have a soma in the dataset, and otherwise at the synapse-count-weighted centroid of its neurons' synapses (sensory neurons, whose cell bodies lie outside the CNS).

**Statistic.** Total wiring cost C = sum over edges of the Euclidean distance between the two nodes' positions, each edge counted once (unweighted).

> **H (primary)**: the real assignment of positions to nodes has a **lower** total wiring cost C than random reassignments of the same set of positions to the same nodes on the same graph.

One-sided test in that direction. N = 1000 uniform random permutations of the position-to-node assignment; the graph, the edge set, and the multiset of positions are unchanged, only which node sits where. Empirical p = (1 + number of permutations with C ≤ real C) / (1 + N); the smallest attainable p is 1/1001. Significance threshold α = 0.05. Effect sizes reported alongside p: z-score of the real cost against the permutation distribution, and the ratio of real cost to mean permuted cost.

**Why unweighted is primary.** Synapse counts per edge span several orders of magnitude, so a synapse-weighted sum is dominated by a small number of very large connections and tests the placement of those few pairs rather than of the network. An unweighted sum over the thresholded graph treats every connection that matters to its target as one wire, the classical component-placement formulation.

**Secondary analyses, same direction, same one-sided test, reported without being substituted for the primary:**

1. Synapse-weighted cost: each edge length multiplied by the edge's synapse count.
2. Within-compartment permutation: positions are shuffled only among nodes of the same compartment (brain-dominant, VNC-dominant, or unclassified, by majority of synapses in `CentralBrain` + `Optic(L)` + `Optic(R)` versus `VNC`). The full permutation moves brain nodes into the nerve cord and is expected to be an easy null to beat; this one asks whether placement is economical beyond the brain / nerve cord split.
3. Synapse-centroid positions for every node, in place of soma positions, with the full permutation.

A result in which the real cost is not lower than the permutations, for the primary or any secondary analysis, is reported as such.
