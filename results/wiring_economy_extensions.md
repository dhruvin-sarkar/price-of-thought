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

## Results

Hypotheses committed in `e62c6df` before any statistic in this file was computed.

### Distance dependence (H5)

| pairs | ordered pairs | edges | probability, first bin | Spearman ρ | p | λ (0–600 µm fit) |
|---|---|---|---|---|---|---|
| all | 532,340,256 | 490,884 | 0.0116 | -0.993 | 9.4e-48 | 76 µm |
| brain-brain | 257,650,652 | 319,431 | 0.0115 | -0.154 | 0.14 | 63 µm |
| vnc-vnc | 49,287,420 | 133,277 | 0.0130 | -0.159 | 0.14 | 128 µm |
| cross | 225,402,184 | 38,176 | 0.0033 | -0.988 | 9.2e-42 | 208 µm |

**H5 is supported** over all pairs (51 bins with at least 1000 pairs). Within one compartment the decline is not monotonic and the rank correlation is not significant: probability falls to a minimum at 340 µm between brain nodes and 500 µm between nerve-cord nodes, then rises again over the longest distances, where pairs are few (2,015 brain and 1,176 nerve-cord edges are 600 µm or longer; 61% and 57% of them join opposite sides, and 0.1% or fewer join a type to its own counterpart). The exponential length constants describe the first 600 µm only. Per-bin counts are in `distance_dependence.csv`.

### Distance from a local optimum (H6)

Of 2,000,000 proposed swaps, 50,050 lowered the total cost and were kept. Total unweighted wiring cost fell from 93,095 mm to 61,778 mm, a reduction of 33.64%. **H6 is supported.** The search is greedy and was stopped at a fixed number of proposals and had not converged: the last 100,000 proposals still saved 0.33% of the starting cost. The reduction is therefore a lower bound on what swaps alone can achieve. The swaps ignore every physical constraint on where cell bodies and neuropils can lie, so the gap measures distance from a wiring-only optimum, not a placement the animal could adopt.

### Where the wiring cost goes (H7)

| edges | count | share of edges | share of wiring cost | mean length |
|---|---|---|---|---|
| neck-crossing | 36,943 | 7.5% | 24.0% | 606 µm |
| connective-incident | 100,126 | 20.4% | 38.7% | 360 µm |
| high-degree-incident | 204,945 | 41.8% | 46.4% | 211 µm |
| none of these | 241,446 | 49.2% | 37.3% | 144 µm |

The first three rows overlap; the last holds edges in none of them.

Edges incident on a node of total degree at least 67 (90th percentile) have mean length 211 µm (median 161) against 175 µm (median 150) for other edges; one-sided Mann-Whitney p < 1e-300. **H7 is supported.**

Placement test within each compartment (positions permuted among that compartment's nodes, edges inside the compartment only), descriptive:

| compartment | edges | real / permuted cost | z | permutations at or below real | p |
|---|---|---|---|---|---|
| brain | 319,431 | 0.679 | -169.8 | 0 of 1000 | 0.0010 |
| vnc | 133,277 | 0.741 | -64.7 | 0 of 1000 | 0.0010 |

### Length and traffic (H8)

Spearman correlation between edge length and directed edge betweenness: ρ = 0.121 over all edges (one-sided p < 1e-300), and ρ = 0.084 over the 452,708 edges inside one compartment (p < 1e-300). **H8 is supported**, with a weak effect. Median edge betweenness by length quartile, shortest first: 1,852, 1,910, 2,147, 2,727.

Across the 1,921 connective nodes with neck-crossing edges, the Spearman correlation between the mean length of those edges and their number is 0.305 (p = 1.03e-42).

![Wiring economy](wiring_economy_extensions.png)
