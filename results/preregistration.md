# Pre-registration index

Each hypothesis was written into the hypothesis section of its results file and committed before the statistic was computed. The scripts only append results beneath that section. This page is an index of those sections, not a separate plan; the wording that counts is the one in each file at its registration commit, which `git show <commit>:results/<file>` prints.

`make verify` checks, through `verify/check_preregistration.py`, that every hypothesis section is unchanged since its registration commit, that each commit predates the first commit of the results it governs, and that each results JSON records the same commit.

| commit | date | what was registered |
|---|---|---|
| `39892c5` | 2026-09-16 | spatial optimality, before the spatial graph existed on disk |
| `e62c6df` | 2026-09-16 | connective rich club, connective value, wiring economy extensions, cable length, generative model |
| `73fba33` | 2026-09-16 | price and value of individual connective cell types, edge-threshold robustness |

## Hypotheses and outcomes

| | hypothesis | direction | file | commit | outcome |
|---|---|---|---|---|---|
| H | real placement is cheaper than permutations of the same positions | lower cost | [spatial_optimality.md](spatial_optimality.md) | `39892c5` | supported |
| H1 | rich-to-rich routes through the connective exceed layer-preserving rewirings | more routes | [connective_richclub.md](connective_richclub.md) | `e62c6df` | supported |
| H2 | rich partners are over-represented among connective partners | enriched | [connective_richclub.md](connective_richclub.md) | `e62c6df` | supported |
| H3 | descending and ascending nodes are over-represented among hubs | odds ratio above 1 | [connective_richclub.md](connective_richclub.md) | `e62c6df` | supported |
| H4 | cutting the neck costs more flow than random wiring of equal length | more flow lost | [connective_value.md](connective_value.md) | `e62c6df` | **not supported** |
| H5 | connection probability falls with distance | negative correlation | [wiring_economy_extensions.md](wiring_economy_extensions.md) | `e62c6df` | supported over all pairs |
| H6 | the real placement is not a local optimum under swaps | saving above 1% | [wiring_economy_extensions.md](wiring_economy_extensions.md) | `e62c6df` | supported |
| H7 | edges of high-degree nodes are longer | longer | [wiring_economy_extensions.md](wiring_economy_extensions.md) | `e62c6df` | supported |
| H8 | edge length correlates with edge betweenness | positive | [wiring_economy_extensions.md](wiring_economy_extensions.md) | `e62c6df` | supported, weak |
| H9 | skeleton cable length correlates with soma-to-output distance | positive | [cable_length.md](cable_length.md) | `e62c6df` | supported |
| H10 | a connective cell type's wire length correlates with the flow it carries | positive, both directions | [connective_price.md](connective_price.md) | `73fba33` | **not supported** |
| H10b | the correlation survives control for the number of connections | positive, both directions | [connective_price.md](connective_price.md) | `73fba33` | **not supported** |
| H11 | placement, routes and hubs keep direction and significance at 0.5%, 2% and 5% | unchanged | [threshold_robustness.md](threshold_robustness.md) | `73fba33` | **not supported** |

The generative model ([generative_model.md](generative_model.md), `e62c6df`) was registered as a protocol without a hypothesis: which of thirteen properties a distance, compartment and cell-class model reproduces was to be reported either way.
