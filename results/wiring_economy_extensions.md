# Further analyses of wiring economy

## Hypotheses (stated before any statistic in this file was computed)

### Distance dependence of connection probability

Connection probability for ordered node pairs, in distance bins of 20 µm, separately for brain–brain, nerve cord–nerve cord and cross-compartment pairs. An exponential P(d) = a · exp(−d / λ) is fitted over 0–600 µm and the length constant λ reported.

> **H5**: connection probability decreases with distance (Spearman correlation between bin centre and bin probability < 0, over bins with at least 1000 pairs).

### Distance from a local optimum

Following Kaiser & Hilgetag (2006) and Gushchin & Tang (2015): 2,000,000 proposed swaps of position between two uniformly chosen soma-placed nodes of the same compartment, each accepted if it lowers total unweighted wiring cost. Nodes placed by synapse centroid (mostly sensory, whose positions are set by the periphery) stay fixed. The cost reduction reached is reported as a lower bound on how far the real placement is from a local optimum under swaps.

> **H6**: the real placement is not a local optimum: cost-reducing swaps exist and together lower the total cost by more than 1%.

### Where the wiring cost goes

Share of total wiring cost against share of edges for: neck-crossing edges, all connective-incident edges, and edges incident on high-degree nodes (total degree at or above the 90th percentile).

> **H7** (the high-cost backbone of van den Heuvel et al. 2012 and Towlson et al. 2013): edges incident on high-degree nodes are **longer** than other edges (one-sided Mann-Whitney U, α = 0.05).

The placement test of `results/spatial_optimality.md` is repeated for the brain-only and nerve cord-only subgraphs (edges within one compartment, positions permuted among that compartment's nodes, 1000 permutations each), descriptively.

### Do long connections carry more traffic

> **H8** (high cost, high capacity): edge length is **positively** correlated with edge betweenness (directed, unweighted shortest paths; Spearman, one-sided, α = 0.05). Repeated for edges within a single compartment, to separate the effect from the neck.

For connective nodes, the Spearman correlation between the mean length of a node's neck-crossing edges and the number of those edges is reported descriptively.

### Cable length validation

Skeletons from neuPrint for a stratified random sample of neurons (100 descending, 100 ascending, 150 central brain intrinsic, 150 nerve cord intrinsic, fixed seed). Total cable length is compared with the Euclidean distance from soma to the centroid of the neuron's presynaptic sites, the geometric quantity node positions stand in for.

> **H9**: skeleton cable length is **positively** correlated with soma-to-output distance (Spearman, one-sided, α = 0.05).

A result against any hypothesis is reported as such.
