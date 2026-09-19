# Launch kit

Drafts for announcing the project. Every number below comes from `results/` and matches the technical report. Links: code <https://github.com/dhruvin-sarkar/price-of-thought>, report <https://github.com/dhruvin-sarkar/price-of-thought/blob/main/paper/report.pdf>. This is the third and last part of a study of one connectome, after ConnectomeLens <https://github.com/dhruvin-sarkar/ConnectomeLens> and Fault Lines <https://github.com/dhruvin-sarkar/fault-lines>.

## Thread (7 posts)

**1** (attach `assets/hero.png`)
Every connection that crosses a fruit fly's neck, from the complete male CNS connectome. They are 7.5% of its connections and a quarter of all its wire. Is that expensive wiring spent the way the human brain spends its hub-to-hub connections? Partly.

**2** (attach `results/spatial_optimality.png`)
First, is the fly wired economically at all? I placed 23,073 cell types (split by side) at the centroid of their cell bodies and summed the length of 490,884 connections. The real layout costs 0.459 times the average of 1000 random reshufflings of the same positions, and none of the reshufflings came close. Shuffling only within brain or within nerve cord gives 0.728.

**3**
Cheaper than random is not optimal. Accepting only swaps that shorten the wire cuts at least 33.6% more, a margin close to the 35.1% a constrained optimization found for worm interneurons (Gushchin & Tang 2015). Wire length is one pressure among several.

**4** (attach `results/connective_richclub.png`)
The descending and ascending neurons that make up the connective sit among the hubs: 24% of them are in the top 10% by degree, against 9% of other cell types. Their partners are also well connected, 1.40 times more often than chance. Lin et al. 2024 expected this from the FlyWire brain; testing it needed a connectome with the nerve cord.

**5** (attach `results/connective_value.png`)
But does the expensive wire buy more? Cutting every neck-crossing connection removes 963 units of sensory-to-motor flow, counted as edge-disjoint paths. Random ordinary wiring of the same total length removes 2,689, and the longest ordinary connections of the same length remove 962. On this measure the connective is worth what long wire is worth. The exception is brain-to-nerve-cord flow, where it removes 1.83 times the random loss.

**6**
Caveats. The hub-to-hub routing excess (1.10 times a degree-preserving null) vanishes at a lower edge threshold, and a model built only from distance, compartment and cell class reproduces it. Across descending and ascending cell types, more wire predicts more flow only through more connections. Node positions track wiring between cell classes, not individual neurons' cable. This is a static wiring diagram and has not been peer reviewed.

**7**
This is the third and last part of a study of one connectome. ConnectomeLens asked whether the wiring alone can find sex-related cell types; Fault Lines asked how much can be removed before sensing stops reaching movement.
Code, report and `make reproduce`: https://github.com/dhruvin-sarkar/price-of-thought
Data: HHMI Janelia FlyEM and Google Research, Berg et al., Cell 2026, doi:10.1016/j.cell.2026.08.015

## Show HN

**Title:** Show HN: What a fruit fly's longest wires cost, and what they buy

**Text:**

The complete connectome of a male *Drosophila* central nervous system (Berg et al., Cell 2026) contains the brain, the ventral nerve cord and the neck connective between them in one animal. That makes two old questions testable across a whole CNS. Is the nervous system laid out to keep its wiring short (Cajal, Cherniak)? And are its longest, most expensive connections reserved for hubs, as in the human connectome's "rich club" (van den Heuvel & Sporns)?

I built a spatially embedded graph from neuPrint's `male-cns:v1.0`. It has 23,073 cell types split by body side, each at the centroid of its neurons' cell bodies, and 490,884 connections that each supply at least 1% of the target's input. Every hypothesis, with its direction and null model, was committed to the repo before it was computed.

What came out:

- the real layout costs 0.459 times random placements of the same positions (z = −278.8), but greedy swaps still cut at least 33.6%: cheaper than random, not optimal
- connections crossing the neck are 7.5% of edges and 24.0% of wire, and descending and ascending cell types are over-represented among hubs (odds ratio 3.22)
- cutting the connective removes 0.36 times the sensory-to-motor flow capacity that random ordinary wiring of the same length does, and as much as the longest ordinary edges of the same length, except from brain to nerve cord (1.83 times)
- the hub-to-hub routing excess (1.10 times a degree-preserving null) disappears at a 0.5% edge threshold, and a logistic model using only distance, compartment and cell class reproduces it
- several pre-registered hypotheses failed, and the report says so

Flow capacity is the Fault Lines metric, reused unchanged: max flow with unit capacities, i.e. edge-disjoint paths. This is the third of three analyses of the same dataset, after ConnectomeLens and Fault Lines. It is a static structural analysis at cell-type resolution and says nothing about behaviour. Everything reproduces with `make reproduce` from public neuPrint data.

Code and report: https://github.com/dhruvin-sarkar/price-of-thought

## Reddit (r/neuroscience)

**Title:** Wiring economy and the brain–nerve cord connective in the complete male Drosophila CNS connectome: placement costs 0.46× random, but neck-crossing wiring buys no more sensory-to-motor flow per unit length than ordinary long wiring

**Body:**

The male CNS connectome from HHMI Janelia FlyEM and Google Research (Berg et al., *Cell* 2026, doi:10.1016/j.cell.2026.08.015) contains brain and nerve cord in one animal. I used it to test wiring economy and rich-club organization across a whole CNS, treating the neck connective as its own class of connections. Prior fly work on both questions (Rivera-Alba 2011, Lin 2024, Salova & Kovács 2025) is confined to the brain; details are in `results/prior_art.md`.

**Setup:**

- 23,073 nodes (cell type × side) from 164,506 typed neurons, each placed at its soma centroid; 490,884 directed edges at ≥ 1% of target input
- wiring cost as summed Euclidean edge length; 36,943 neck-crossing edges (DN → VNC, VNC → DN, AN → brain, brain → AN)
- all hypotheses and their directions committed before computation

**Results:**

- placement costs 0.459 × the mean of 1000 permutations (primary), 0.728 × within compartments, 0.679 × brain only and 0.741 × nerve cord only; greedy swaps cut ≥ 33.6% further
- connection probability decays with distance (λ = 76 µm), but not monotonically within brain or nerve cord
- neck-crossing edges are 7.5% of edges and 24.0% of wire; edges of high-degree nodes are longer (211 vs 175 µm)
- connective partners are enriched for high degree (1.40 ×); DN/AN are over-represented among hubs (odds ratio 3.22)
- rich-to-rich routes through the connective vs layer-preserving rewiring: 1.103 × (p = 0.001), all from ascending routes; 1.002 × at a 0.5% threshold
- value: cutting the connective costs 963 of 8,731 units of sensory-to-motor flow, against these comparison sets:
  - cost-matched random ordinary wiring: 2,689 (ratio 0.36)
  - count-matched random ordinary wiring: 648 (ratio 1.49)
  - the longest ordinary edges of equal total length: 962
  - brain → nerve cord flow only: 1.83 × the cost-matched loss
- per cell type, price (wire length) and value (flow lost) correlate only through edge count (partial ρ = 0.044 for DNs, −0.12 for ANs)
- a generative logistic model (distance + compartment + superclass pairing, pseudo-R² 0.276, AUC 0.848) reproduces 2 of 13 graph properties, including the rich-to-rich route count

**Caveats I would flag first:**

- Positions are soma centroids of cell types. A 500-neuron skeleton check shows they track cable length between classes (ρ = 0.43) but not within them.
- Flow capacity counts unweighted edge-disjoint paths, which favours many short connections. That is why the cost-matched primary is reported alongside the count-matched and longest-edge comparisons.
- Sensory ascending neurons also cross the neck, but they are treated as sensory because they have no CNS soma.
- The swap search ignores physical constraints on where neuropils can sit.

This is the third and last part of a study of this connectome, after ConnectomeLens and Fault Lines. I'd welcome criticism of the cost-matched null in particular.

Code and technical report: https://github.com/dhruvin-sarkar/price-of-thought

## awesome-fly entry (draft)

For a pull request to `cobanov/awesome-fly`, following its `CONTRIBUTING.md`. The list already carries ConnectomeLens as Wired Different, at the end of "Brain models and embodied simulation"; the pull request adds the two later parts directly below it, in the list's entry format. Both use the complete retained cell-type graph, not an extracted circuit, and have no demo yet.

```markdown
- [Fault Lines](https://github.com/dhruvin-sarkar/fault-lines) by **dhruvin-sarkar** - pre-registered attack-tolerance analysis of the male CNS connectome (male-cns v1.0) cell-type graph, measuring how sensory-to-motor flow capacity collapses under random and targeted removal, against degree-preserving null graphs. [Technical report](https://github.com/dhruvin-sarkar/fault-lines/blob/main/paper/report.pdf).
- [The Price of Thought](https://github.com/dhruvin-sarkar/price-of-thought) by **dhruvin-sarkar** - pre-registered wiring-economy and rich-club analysis of the male CNS connectome (male-cns v1.0) with cell types placed at their soma centroids, testing placement against permutations and the flow value of the brain–nerve cord connective against cost-matched wiring. Structural analysis at cell-type resolution. [Technical report](https://github.com/dhruvin-sarkar/price-of-thought/blob/main/paper/report.pdf).
```

Pull request title: Add Fault Lines and The Price of Thought

Pull request description:

> Adds two analyses of the male CNS connectome (Berg et al. 2026) by the author of Wired Different, which is already listed; the three analyse the same dataset. Fault Lines measures how sensory-to-motor routing degrades as cell types or connections are removed. The Price of Thought measures wiring cost and what the brain–nerve cord connective contributes against cost-matched wiring. Both are pre-registered, use the complete cell-type graph, and report results that did not support their hypotheses. Links and reports verified.
