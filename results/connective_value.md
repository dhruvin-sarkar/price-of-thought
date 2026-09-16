# Value of the connective against its wiring cost

## Hypothesis (stated before any statistic in this file was computed)

**Metrics.** The Fault Lines definitions, with the code copied byte for byte (`pipeline/connectivity_metrics.py`): flow capacity, the maximum number of edge-disjoint directed paths from any sensory node to any motor node (primary); reachable pairs, the number of (sensory, motor) node pairs joined by a directed path (secondary).

**Sets.** Sensory nodes S: majority superclass `cb_sensory`, `ol_sensory`, `vnc_sensory`, `sensory_ascending` or `sensory_descending` (the Fault Lines sensory set). Motor nodes M: majority superclass `cb_motor` or `vnc_motor`. Fault Lines also counted descending neurons as motor outputs; they are excluded here because they are part of what is removed.

**The connective.** The primary removal set X is the set of edges whose wire crosses the neck: DN → V, V → DN, AN → B and B → AN, where DN and AN are connective nodes and B and V are non-connective nodes of the brain and nerve-cord compartments. Descending neurons have their somata in the brain and ascending neurons in the nerve cord, so each of these edges joins a connective node to a partner on the far side of the neck.

**Cost.** The cost of an edge set is the sum of its Euclidean edge lengths between node positions (`results/spatial_graph.md`).

**Null.** 1000 random sets of non-connective edges (neither endpoint a connective node) matched to the total cost of X: edges are taken in a uniformly random order and added while the running total stays at or below the cost of X, then the next edge is added if that brings the total closer to the target. The achieved cost of every set is recorded and its ratio to the cost of X reported.

**Statistic.** The loss Δ = value of the intact graph − value after removing the set.

> **H4 (primary)**: removing the neck-crossing edges reduces sensory-to-motor flow capacity **more** than removing random non-connective edges of equal total wiring cost: Δflow(X) > Δflow(null).

One-sided empirical p = (1 + number of null Δ ≥ real Δ) / (1 + N), α = 0.05, reported with the ratio of losses and the z-score.

**Secondary analyses.**

1. The same test on reachable pairs.
2. The same test for the set of all edges incident on a connective node (silencing descending and ascending neurons rather than cutting the neck), with its own cost-matched null of 1000 sets.
3. The same test for X against 1000 random non-connective sets matched on edge count instead of cost.
4. X against the longest non-connective edges, taken in decreasing length until the cost of X is matched (a single deterministic comparison, reported descriptively).
5. Cross-compartment flow capacity, from brain sensory nodes to nerve-cord motor nodes and from nerve-cord sensory nodes to brain motor nodes, evaluated on the same primary null sets.

A result against any hypothesis is reported as such.
