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

## Procedure

Hypotheses committed in `e62c6df` before any statistic in this file was computed.

- Sensory nodes: 751 (390 brain, 361 nerve cord). Motor nodes: 367 (86 brain, 281 nerve cord).
- Neck-crossing edges: 36,943, total length 22.37 m, mean 606 µm.
- All connective-incident edges: 100,126, total length 36.05 m, mean 360 µm.
- Non-connective edges available for the null sets: 390,758, mean length 146 µm.
- 1000 random sets, neck-crossing edges vs random non-connective edges of equal cost (primary): 153,244 edges on average (152,667–153,763); achieved cost 1.0000–1.0000 of the connective set's cost.
- 1000 random sets, all connective-incident edges vs random non-connective edges of equal cost: 246,922 edges on average (246,369–247,444); achieved cost 1.0000–1.0000 of the connective set's cost.
- 1000 random sets, neck-crossing edges vs random non-connective edges of equal count: 36,943 edges on average (36,943–36,943); achieved cost 0.2386–0.2434 of the connective set's cost.

## Result: neck-crossing edges against equal wiring cost (H4)

| value | intact | lost, connective | lost, random mean ± sd | random ≥ connective | ratio | z | p |
|---|---|---|---|---|---|---|---|
| flow capacity | 8,731 | 963 | 2,689.3 ± 40.6 | 1000 / 1000 | 0.36 | -42.5 | 1.0000 |
| reachable pairs | 269,011 | 0 | 3,490.3 ± 915.6 | 1000 / 1000 | 0.00 | -3.8 | 1.0000 |
| flow, brain sensory to nerve-cord motor | 6,423 | 3,759 | 2,051.8 ± 35.4 | 0 / 1000 | 1.83 | 48.2 | 0.0010 |
| flow, nerve-cord sensory to brain motor | 2,228 | 242 | 554.8 ± 19.2 | 1000 / 1000 | 0.44 | -16.3 | 1.0000 |

**H4 is not supported.** Cutting the 36,943 neck-crossing edges removes 963 units of sensory-to-motor flow capacity; random non-connective wiring of the same total length removes 2,689.3 on average (ratio 0.36, z = -42.5, p = 1.0000).

The loss is concentrated in one direction. Of the 6,423 units of flow from brain sensory to nerve-cord motor nodes, the cut removes 3,759, 1.83 times the random loss (p = 0.0010); of the 2,228 units in the other direction it removes 242, 0.44 times the random loss. Reachable sensory-motor pairs are unchanged by the cut (0 lost), so every pair it touches stays joined by a path that avoids the neck-crossing edges.

## Secondary: silencing every connective edge, equal cost

| value | intact | lost, connective | lost, random mean ± sd | random ≥ connective | ratio | z | p |
|---|---|---|---|---|---|---|---|
| flow capacity | 8,731 | 2,118 | 4,337.5 ± 40.1 | 1000 / 1000 | 0.49 | -55.4 | 1.0000 |
| reachable pairs | 269,011 | 1,101 | 9,415.2 ± 1,517.1 | 1000 / 1000 | 0.12 | -5.5 | 1.0000 |
| flow, brain sensory to nerve-cord motor | 6,423 | 6,202 | 3,359.4 ± 34.9 | 0 / 1000 | 1.85 | 81.4 | 0.0010 |
| flow, nerve-cord sensory to brain motor | 2,228 | 1,543 | 896.2 ± 17.8 | 0 / 1000 | 1.72 | 36.4 | 0.0010 |

## Secondary: neck-crossing edges against equal edge count

| value | intact | lost, connective | lost, random mean ± sd | random ≥ connective | ratio | z | p |
|---|---|---|---|---|---|---|---|
| flow capacity | 8,731 | 963 | 648.2 ± 23.7 | 0 / 1000 | 1.49 | 13.3 | 0.0010 |
| reachable pairs | 269,011 | 0 | 636.7 ± 477.7 | 1000 / 1000 | 0.00 | -1.3 | 1.0000 |
| flow, brain sensory to nerve-cord motor | 6,423 | 3,759 | 464.2 ± 20.4 | 0 / 1000 | 8.10 | 161.8 | 0.0010 |
| flow, nerve-cord sensory to brain motor | 2,228 | 242 | 133.8 ± 11.1 | 0 / 1000 | 1.81 | 9.8 | 0.0010 |

## Secondary: the longest non-connective edges

The 84,008 longest non-connective edges (all at least 207 µm) match the neck-crossing edges in total length. Removing them loses: flow capacity 962; reachable pairs 1,101; flow, brain sensory to nerve-cord motor 1,122; flow, nerve-cord sensory to brain motor 172.

![Connective value](connective_value.png)
