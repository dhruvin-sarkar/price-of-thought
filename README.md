# The Price of Thought

Wiring cost and the brain–nerve cord connective in the complete *Drosophila* male central nervous system connectome.

![The male fly central nervous system seen from the front, brain above and nerve cord below, with every connection that crosses the neck drawn as a line coloured by its length, from pale orange for short to dark red for the longest, about a millimetre.](assets/hero.png)

**Does the fly wire its nervous system economically, and does it spend its longest wires the way the human brain spends its hub connections?** Partly. Cell types are placed so that their connections cost less than half as much wire as random placements would, though far from the cheapest arrangement possible. The descending and ascending neurons of the neck connective carry a quarter of all wire in 7.5% of the connections, and they sit among the most connected cell types. That wiring carries no more sensory-to-motor flow per unit length than ordinary long wiring, except in the direction from brain to nerve cord.

<sub>Dhruvin Sarkar. An independent, pre-registered analysis of public connectome data, not peer reviewed.</sub>

[Technical report (PDF)](paper/report.pdf) · [Prior art and scope](results/prior_art.md)

## Results

Every hypothesis below was committed with its direction, statistic and null before it was computed (commits `39892c5`, `e62c6df`, `73fba33`). Each results file keeps that section unchanged, and the scripts only append beneath it. Hypotheses that were not supported are reported as such.

| question | result | hypothesis |
|---|---|---|
| Is cell-type placement cheaper than random? | 0.459 × the cost of 1000 position permutations, none as cheap (z = −278.8); 0.728 × when shuffled within brain or nerve cord only | supported |
| Is it a local optimum? | No: cost-reducing swaps cut at least 33.6% of the wire | supported (not optimal) |
| Does connection probability fall with distance? | Yes, length constant 76 µm, but not monotonically within brain or nerve cord | supported |
| Are edges of high-degree nodes longer? | Mean 211 against 175 µm | supported |
| Do rich-to-rich routes through the connective exceed a degree-preserving null? | 1.103 ×, p = 0.001, from ascending routes only | supported |
| Are the connective's partners enriched for high degree? | 1.40 × a degree-matched null | supported |
| Are descending and ascending types over-represented among hubs? | Odds ratio 3.22, p = 1.5 × 10⁻⁷⁹ | supported |
| Does cutting the connective cost more flow than random wiring of equal length? | 0.36 × (963 against 2,689 units); 1.83 × from brain to nerve cord | **not supported** |
| Do more expensive connective cell types carry more flow? | Only through their number of connections (partial ρ = 0.044) | **not supported** |
| Do the placement, route and hub results hold at edge thresholds of 0.5%, 2%, 5%? | Placement and hubs yes; rich-to-rich routes vanish at 0.5% | **not supported** |
| What does a distance + compartment + cell-class model reproduce? | 2 of 13 properties, including the rich-to-rich route count | reported |

Full reports:

- [spatial_optimality.md](results/spatial_optimality.md): placement against 1000 permutations
- [wiring_economy_extensions.md](results/wiring_economy_extensions.md): distance dependence, swaps, where the wire goes, length and traffic
- [cable_length.md](results/cable_length.md): node positions checked against skeleton cable length
- [connective_richclub.md](results/connective_richclub.md): rich-club routing, partner enrichment, hubs
- [connective_value.md](results/connective_value.md): value of the connective against cost-matched wiring
- [connective_price.md](results/connective_price.md): price and value of individual descending and ascending cell types
- [generative_model.md](results/generative_model.md): logistic wiring models and 50 synthetic graphs per model
- [threshold_robustness.md](results/threshold_robustness.md): the headline tests at three other edge thresholds

## Data and graph

Data are the male CNS connectome, `male-cns:v1.0` on neuPrint (Berg et al., *Cell* 2026). Each node is a cell type on one side of the body, placed at the centroid of its neurons' cell bodies. A connection counts when it supplies at least 1% of the target's input synapses. The result is 23,073 nodes and 490,884 connections, 36,943 of them crossing the neck between brain and nerve cord. Details are in [spatial_graph.md](results/spatial_graph.md) and [schema.md](results/schema.md).

Flow capacity, reachability and degree-preserving rewiring are the Fault Lines implementations, copied unchanged.

## Reproducing

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
make reproduce PYTHON=.venv/bin/python
```

`make reproduce` pulls from neuPrint, builds the graph, runs every analysis, renders the hero image and builds the PDF. A neuPrint token in `NEUPRINT_APPLICATION_CREDENTIALS` is used when set; the public dataset is also readable without one. The PDF needs pandoc and typst. The analyses use multiprocessing and were run on a machine with 16 GB of RAM; worker counts are set in the `Makefile`. `make test` runs the test suite, which CI runs on every push.

## A three-part study

This is the third of three analyses of the same connectome:

1. [ConnectomeLens](https://github.com/dhruvin-sarkar/ConnectomeLens) asks whether the male wiring alone identifies the cell types annotated as sexually dimorphic.
2. [Fault Lines](https://github.com/dhruvin-sarkar/fault-lines) asks how much of the nervous system can be removed before sensory input no longer reaches motor output.
3. The Price of Thought asks what the wiring costs, and what its most expensive part buys.

## Citation

See [CITATION.cff](CITATION.cff). Please also cite the connectome: Berg S, et al. (2026). Sexual dimorphism in the complete *Drosophila* male central nervous system connectome. *Cell* 189(18):5504–5526. doi:10.1016/j.cell.2026.08.015

## License

MIT
