# Price and value of individual connective cell types

## Hypothesis (stated before any statistic in this file was computed)

**Units.** Every connective node c (a descending or ascending cell type on one side) with at least one neck-crossing edge (`results/connective_value.md`): DN → V and V → DN edges for a descending node, AN → B and B → AN edges for an ascending node.

**Price.** The summed Euclidean length of c's neck-crossing edges.

**Value.** The loss of flow capacity when c's neck-crossing edges alone are removed from the intact graph, in the direction the node carries: brain sensory to nerve-cord motor flow for a descending node, nerve-cord sensory to brain motor flow for an ascending node. The loss of whole-CNS sensory-to-motor flow is recorded as well. Metrics and sets are those of `results/connective_value.md`.

> **H10**: across connective nodes, price and value are **positively** correlated (Spearman, one-sided, α = 0.05), tested separately for descending and ascending nodes; supported if both are significant.

> **H10b**: the correlation survives control for the number of neck-crossing edges: the partial Spearman correlation of price and value given edge count (Pearson correlation of rank residuals after linear regression of each rank on the rank of edge count) is **positive** (one-sided, α = 0.05), separately for descending and ascending nodes; supported if both are significant. H10 alone could follow from nodes with more edges being both costlier and more valuable; H10b asks whether, at a given number of connections, longer wiring buys more flow.

Reported descriptively: the fraction of nodes whose removal costs no flow, the most valuable and the most expensive cell types, and value per millimetre of wire.

A result against either hypothesis is reported as such.
