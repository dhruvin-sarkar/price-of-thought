# Rich-club structure of the connective

## Hypothesis (stated before any statistic in this file was computed)

**Sets.** Connective nodes are the (cell type, hemisphere) nodes of descending (DN) and ascending (AN) cell types (`results/connective_set.json`). Partner nodes are all other nodes, split by compartment into brain partners B and nerve-cord partners V (`results/spatial_graph.md`).

**Layers of connective edges.** D_in: B → DN. D_out: DN → V. A_in: V → AN. A_out: AN → B. A route through the connective is a two-edge path b → c → v (descending) or v → c → b (ascending) through one connective node c.

**Richness.** A partner's richness is its total degree (in + out) in the subgraph induced on non-connective nodes, so that no connective edge contributes to it. The rich brain set is the brain partners whose richness is at or above the 90th percentile of richness among brain partners; the rich nerve-cord set is defined the same way within V.

**Statistic.** R = the number of rich-to-rich routes = sum over DN nodes of (rich brain inputs × rich nerve-cord outputs) + sum over AN nodes of (rich nerve-cord inputs × rich brain outputs).

**Null.** Each of the four layers is randomized independently with the degree-preserving edge swaps used in Fault Lines (`pipeline/rewiring.py`, 10 swaps per edge, no multi-edges). Every partner keeps its number of edges to connective nodes in each layer and every connective node keeps its in- and out-degree in each layer; only which partner attaches to which connective node changes. N = 1000 randomizations.

> **H1 (primary)**: rich-to-rich routes through the connective are **more** numerous in the real graph than in the layer-randomized graphs: R_real > R_null.

One-sided empirical p = (1 + number of null R ≥ real R) / (1 + N), α = 0.05, reported with the ratio R_real / mean R_null and the z-score.

**Secondary analyses.**

1. H1 separately for descending and for ascending routes.
2. R at richness thresholds of the top 1, 2, 5, 20, 30 and 50% (a curve; the 10% threshold is the primary).
3. **Endpoint enrichment. H2**: rich partners are over-represented among the partners of connective nodes. Statistic: the fraction of layer edges whose partner endpoint is rich. Null: for each connective node, its partners in each layer are redrawn uniformly without replacement from all eligible partners (B or V), holding the node's degree in that layer; N = 1000; one-sided upper p.
4. **Whole-CNS rich club (the expectation of Lin et al. 2024).** Rich-club coefficient φ(k) = E(>k) / (N(>k) (N(>k) − 1)) on the full directed graph, with k the total degree, normalized by the mean over 100 degree-preserving randomizations of the full graph. The rich-club regime is the set of k at which real φ(k) exceeds all 100 randomized values. **H3**: DN and AN nodes are over-represented among nodes whose total degree is at or above the 90th percentile of the whole graph (one-sided Fisher exact test, α = 0.05). The share of DN and AN nodes above the lowest degree of the rich-club regime is reported descriptively.

A result against any hypothesis is reported as such.

## Procedure

Hypotheses committed in `e62c6df` before any statistic in this file was computed.

- Connective nodes: 951 descending, 1,096 ascending. Partners: 14,950 brain, 6,076 nerve cord.
- Layer edges: D_in 13,270, D_out 17,628, A_in 12,357, A_out 16,677.
- Rich partners (top 10%): richness at or above 60 in the brain and 58 in the nerve cord.
- 1000 layer randomizations; 100 whole-graph randomizations for the rich-club coefficient.

## Result: rich-to-rich routes (H1)

| routes | real | randomized mean ± sd | randomized ≥ real | real / randomized | z | p |
|---|---|---|---|---|---|---|
| all (primary) | 7,454 | 6,760 ± 143 | 0 / 1000 | 1.103 | 4.8 | 0.0010 |
| descending | 1,911 | 1,941 ± 61 | 709 / 1000 | 0.984 | -0.5 | 0.7093 |
| ascending | 5,543 | 4,819 ± 127 | 0 / 1000 | 1.150 | 5.7 | 0.0010 |

**H1 is supported.** Real rich-to-rich routes: 1.103 times the randomized mean (z = 4.8, p = 0.0010).

### By richness threshold

| top % of partners counted as rich | rich brain | rich nerve cord | real routes | randomized mean | real / randomized | z | p |
|---|---|---|---|---|---|---|---|
| 1 | 150 | 61 | 56 | 48 | 1.170 | 1.1 | 0.1548 |
| 2 | 303 | 124 | 215 | 231 | 0.933 | -0.8 | 0.8092 |
| 5 | 764 | 313 | 2,229 | 2,020 | 1.103 | 3.1 | 0.0020 |
| 10 | 1,541 | 617 | 7,454 | 6,760 | 1.103 | 4.8 | 0.0010 |
| 20 | 2,991 | 1,276 | 21,792 | 21,343 | 1.021 | 1.6 | 0.0629 |
| 30 | 4,665 | 1,853 | 44,989 | 43,871 | 1.025 | 2.6 | 0.0040 |
| 50 | 7,666 | 3,197 | 108,343 | 107,396 | 1.009 | 1.4 | 0.0849 |

## Result: rich partners among connective partners (H2)

14.4% of connective layer edges have a rich partner, against 10.2% ± 0.1% when each connective node's partners are redrawn uniformly (ratio 1.40, z = 33.9, p = 0.0010). **H2 is supported.**

## Result: descending and ascending neurons in the whole-CNS rich club (H3)

Nodes with total degree at or above the 90th percentile (67): 24.4% of descending nodes, 23.2% of ascending nodes, 8.8% of all other nodes. One-sided Fisher exact test: odds ratio 3.22, p = 1.48e-79. **H3 is supported.**

The lowest total degree at which the real rich-club coefficient exceeds all 100 randomized graphs is k = 12 (every such k is listed in `connective_richclub.json`). 22,926 nodes have degree above k = 12: 99.7% of descending nodes, 99.9% of ascending nodes and 99.3% of other nodes; connective nodes make up 8.9% of that set.

Normalized rich-club coefficient at selected degrees: k = 10: 1.00, k = 20: 1.00, k = 40: 1.02, k = 60: 1.11, k = 80: 1.37, k = 100: 1.70, k = 150: 1.91, k = 200: 2.13.

Descriptively, because exceedance of every randomized graph already holds where the excess is negligible, the normalized coefficient first reaches 1.1 from k = 59 (3,277 nodes above); 1.5 from k = 88 (922 nodes above); 2 from k = 172 (126 nodes above).

![Connective rich club](connective_richclub.png)
