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
