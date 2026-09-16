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

## Procedure

The hypothesis above was committed in `39892c5` before the spatial graph was built.

- Graph: 23,073 (cell type, hemisphere) nodes and 490,884 directed edges. 22,139 nodes are placed at their soma centroid and 934 at their synapse centroid.
- Real edge lengths: median 154.3 µm, mean 189.6 µm, 95th percentile 562.2 µm, maximum 1003.9 µm.
- Permutations: 1000 per analysis, seeded from 20560916. Compartment groups for the within-compartment analysis: brain 16,052, vnc 7,021 nodes.

## Result

| analysis | real cost | permuted mean ± sd | permuted range | permutations ≤ real | z | real / permuted | p | p < 0.05 |
|---|---|---|---|---|---|---|---|---|
| Soma positions, unweighted cost, all nodes permuted (primary) | 9.309e+07 µm | 2.03e+08 ± 3.94e+05 | 2.018e+08 – 2.041e+08 | 0 / 1000 | -278.8 | 0.459 | 0.0010 | yes |
| Synapse-weighted cost | 1.034e+10 µm·synapses | 3.231e+10 ± 5.9e+08 | 3.041e+10 – 3.406e+10 | 0 / 1000 | -37.3 | 0.320 | 0.0010 | yes |
| Permutation within compartment | 9.309e+07 µm | 1.279e+08 ± 2.22e+05 | 1.271e+08 – 1.287e+08 | 0 / 1000 | -156.9 | 0.728 | 0.0010 | yes |
| Synapse-centroid positions | 4.88e+07 µm | 1.76e+08 ± 3.77e+05 | 1.748e+08 – 1.773e+08 | 0 / 1000 | -337.4 | 0.277 | 0.0010 | yes |

## Reading

Primary analysis: the real placement costs 0.459 times the mean permuted placement (z = -278.8, p = 0.0010; 0 of 1000 permutations at or below the real cost). H is supported.

- Synapse-weighted cost: real cost lower than the permuted mean, ratio 0.320, z = -37.3, p = 0.0010.
- Permutation within compartment: real cost lower than the permuted mean, ratio 0.728, z = -156.9, p = 0.0010.
- Synapse-centroid positions: real cost lower than the permuted mean, ratio 0.277, z = -337.4, p = 0.0010.

With 1000 permutations the smallest attainable p is 0.0010, so the z-score and the cost ratio carry the size of the effect. The test compares the real placement with random placements of the same positions; it does not show that the real placement is the cheapest possible one.

![Permutation distributions](spatial_optimality.png)
