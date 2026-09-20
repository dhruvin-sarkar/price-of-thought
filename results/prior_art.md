# Prior art and the scope of this study

This note records what earlier work has already established about wiring economy, rich-club organization and the descending/ascending connective in *Drosophila*, and states the narrower contribution this study makes against it. Unless marked otherwise, each entry was checked against the full text; citation details were confirmed against Crossref.

## The two FlyWire network papers

### Grindrod, Lambiotte & Sahasrabuddhe, "Modularity, Hierarchical Flows and Symmetry of the Drosophila Connectome" (arXiv:2412.13202, v1, December 2024)

- **Data.** FlyWire (FAFB) connectivity tables from Codex, restricted to neurons of the "Central" super-class and to connections of at least 5 synapses: 32,272 neurons and 849,981 directed, unweighted edges. No optic lobes, no ventral nerve cord, no connective.
- **Methods.** Infomap community detection; geometric description of modules (Hausdorff dimension, comparison with k-means partitions of neuron positions); left-right symmetry of modules by Wasserstein distance; SpringRank hierarchy. The only null model randomizes edge direction while holding inter-module edge counts fixed.
- **Findings.** 67 modules, of which 21 carry 94% of the flow; modules are spatially interleaved rather than compact (adjusted mutual information 0.35 with a 21-cluster spatial partition); the central brain has a Hausdorff dimension near 2.5 while individual modules fall below 2; the hierarchy is significant against its null.
- **Not addressed.** Wiring cost, distance dependence of connection probability, rich-club structure (the paper refers to Lin et al. 2024 for it), generative models, the nerve cord, and cell-type-level analysis.

### Sulyok, Balogh & Palla, "Network geometry of the Drosophila brain" (arXiv:2602.16417, v1, February 2026)

- **Data.** FlyWire (FAFB) brain connectome after cleaning: 132,483 neurons and 2,509,503 edges. The ascending (1,989) and descending (1,276) neurons it contains are represented only by the parts of those neurons inside the brain volume.
- **Methods.** Two-dimensional hyperbolic embedding (CLOVE) and Node2vec embeddings of 2 to 512 dimensions, each compared with the real three-dimensional neuron coordinates on mapping accuracy, greedy routing success, and link prediction from embedded distance. No network null models.
- **Findings.** Real 3D coordinates predict which neurons are connected with AUC 0.862 but support greedy routing in only 7.5% of attempts; the 2D hyperbolic embedding scores higher on every measure (AUC 0.960, greedy success 0.553), and Node2vec overtakes it at roughly 16 dimensions.
- **Not addressed.** Wiring cost or placement tests, rich-club tests, generative network models, the nerve cord and connective, removal experiments, and cell types.

## Work that narrows the claim

**Wiring economy in the fly has been tested before, inside the brain.**

- Rivera-Alba et al. 2011 reconstructed a single lamina cartridge and found its real neuron arrangement cheaper in wiring than one million random rearrangements.
- Salova & Kovács 2025 shuffled neuron positions across the hemibrain (16,804 neurons) and found shuffled layouts roughly twice as costly as the real one; they also found connection probability decaying exponentially with distance and fitted generative models combining degree with wiring length. This overlaps the placement test and the generative model here, at neuron level and within the central brain.
- Péntek & Ercsey-Ravasz 2025 fitted an exponential distance rule network model to FlyWire neuropils.

**A rich club has been shown in the fly brain.** Lin et al. 2024, on FlyWire v630, found a neuron-level rich club against a degree-preserving null, beginning at total degree 37 and containing about 30% of neurons; against a null that also preserves connection densities between neuropils, the excess disappears. Their Discussion anticipates the question asked here: they expect ascending and descending neurons to belong to a central-nervous-system-wide rich club, and note that verifying this awaits a complete CNS connectome. Earlier rich-club reports on light-microscopy data (Shih et al. 2015, abstract read only; Worrell et al. 2017) are not synapse-resolution. Ceballos et al. 2026 report no rich club among descending-neuron axo-axonic connections in the male nerve cord, apparently without a null model.

**The connective has already been identified as a bottleneck, by other measures.**

- Berg et al. 2026, the male CNS connectome analysed here, computed maximum flow from sensory modalities to motor domains across the whole CNS and found ascending and descending neurons to have much higher flow utilization, describing the neck connective as a key bottleneck. This was read in the bioRxiv preprint (v2, October 2025); the published version could differ. The value test here therefore does not introduce flow analysis of the connective: its contribution is the removal of the connective against a null of non-connective connections matched on total wiring cost.
- Bates et al. 2026, the female brain-and-nerve-cord connectome (BANC), found ascending and descending neurons to have higher betweenness on sensory-to-effector shortest paths and disproportionately many partners outside their own network. It contains no wiring-cost analysis, rich-club test, spatial or degree-preserving null, generative model, or cost-matched removal.
- Stürner et al. 2025 compare descending and ascending neuron connectivity across datasets without wiring-cost or rich-club analyses.

**Placement cheaper than random is not placement that is optimal.** In *C. elegans*, Chen, Hall & Chklovskii 2006 report optimized, actual and random wiring costs in the ratio 1 : 4 : 16; Kaiser & Hilgetag 2006 find that rearranging components can cut total wiring by about 48%, because long-range projections that shorten processing paths are kept; Ahn, Jeong & Kim 2006 (read as the arXiv preprint) and Gushchin & Tang 2015 (real layout 30.6% cheaper than random, while a constrained optimization of 86 interneurons cuts a further 35.1%) reach the same conclusion. Towlson et al. 2013 find that an 11-neuron rich club in *C. elegans* accounts for 48% of total wiring cost, the invertebrate counterpart of the high-cost, high-capacity backbone described by van den Heuvel et al. 2012.

## Contribution of this study

To our knowledge, this is the first test of wiring economy and rich-club organization on a single synapse-resolution connectome of an entire central nervous system, the *Drosophila* male CNS, with the brain–nerve cord connective treated as its own class of long-range connections. Earlier fly work on wiring economy and rich clubs is confined to the brain or a part of it, and the two whole-CNS connectome papers identify the connective as a bottleneck without measuring its wiring cost, testing it for rich-club structure, or comparing its removal with a cost-matched null. At cell-type resolution, this study adds:

1. a placement permutation test spanning brain, nerve cord and connective, read, following Kaiser & Hilgetag, as evidence that placement is cheaper than random rather than optimal;
2. a degree-preserving test of whether connective routes preferentially join high-degree types on the two sides, which addresses directly the expectation stated by Lin et al. 2024;
3. the loss of sensory-to-motor reachability and flow capacity when the connective is removed, compared with removing non-connective connections of equal total wiring cost;
4. a test of whether a generative model built on distance, compartment and cell class reproduces these connective-specific statistics.

It does not claim to be the first wiring-economy, rich-club, or connective-flow analysis in the fly.

## References

- Ahn Y-Y, Jeong H, Kim BJ (2006). Wiring cost in the organization of a biological neuronal network. *Physica A* 367:531–537. doi:10.1016/j.physa.2005.12.013
- Bates AS, Phelps JS, Kim M, Yang HH, et al. (2026). Distributed control circuits across a brain-and-cord connectome. *Nature* 656(8129):957–970. doi:10.1038/s41586-026-10735-w
- Berg S, et al. (2026). Sexual dimorphism in the complete *Drosophila* male central nervous system connectome. *Cell* 189(18):5504–5526.e15. doi:10.1016/j.cell.2026.08.015
- Betzel RF, et al. (2016). Generative models of the human connectome. *NeuroImage* 124:1054–1064. doi:10.1016/j.neuroimage.2015.09.041
- Bullmore E, Sporns O (2012). The economy of brain network organization. *Nat Rev Neurosci* 13(5):336–349. doi:10.1038/nrn3214
- Ceballos C, et al. (2026). The *Drosophila* connectome reveals axo-axonic synapses on descending neurons. *iScience* 29(5):115624. doi:10.1016/j.isci.2026.115624
- Chen BL, Hall DH, Chklovskii DB (2006). Wiring optimization can relate neuronal structure and function. *PNAS* 103(12):4723–4728. doi:10.1073/pnas.0506806103
- Cherniak C (1994). Component placement optimization in the brain. *J Neurosci* 14(4):2418–2427. doi:10.1523/JNEUROSCI.14-04-02418.1994
- Cherniak C (1995). Neural component placement. *Trends Neurosci* 18(12):522–527. doi:10.1016/0166-2236(95)98373-7
- Colizza V, Flammini A, Serrano MA, Vespignani A (2006). Detecting rich-club ordering in complex networks. *Nat Phys* 2(2):110–115. doi:10.1038/nphys209
- Grindrod P, Lambiotte R, Sahasrabuddhe R (2024). Modularity, hierarchical flows and symmetry of the Drosophila connectome. arXiv:2412.13202
- Gushchin A, Tang A (2015). Total wiring length minimization of *C. elegans* neural network: a constrained optimization approach. *PLOS ONE* 10(12):e0145029. doi:10.1371/journal.pone.0145029
- Kaiser M, Hilgetag CC (2006). Nonoptimal component placement, but short processing paths, due to long-distance projections in neural systems. *PLoS Comput Biol* 2(7):e95. doi:10.1371/journal.pcbi.0020095
- Lin A, et al. (2024). Network statistics of the whole-brain connectome of *Drosophila*. *Nature* 634(8032):153–165. doi:10.1038/s41586-024-07968-y
- Maslov S, Sneppen K (2002). Specificity and stability in topology of protein networks. *Science* 296(5569):910–913. doi:10.1126/science.1065103
- Péntek B, Ercsey-Ravasz M (2025). The exponential distance rule-based network model predicts topology and reveals functionally relevant properties of the *Drosophila* projectome. *Netw Neurosci* 9(3):869–895. doi:10.1162/netn_a_00455
- Ramón y Cajal S (1909–1911). *Histologie du système nerveux de l'homme et des vertébrés*, trans. L. Azoulay. Paris: Maloine. English translation by N. Swanson and L. W. Swanson (1995), *Histology of the Nervous System of Man and Vertebrates*, Oxford University Press.
- Rivera-Alba M, et al. (2011). Wiring economy and volume exclusion determine neuronal placement in the *Drosophila* brain. *Curr Biol* 21(23):2000–2005. doi:10.1016/j.cub.2011.10.022
- Salova A, Kovács IA (2025). Combined topological and spatial constraints are required to capture the structure of neural connectomes. *Netw Neurosci* 9(1):181–206. doi:10.1162/netn_a_00428
- Shih C-T, et al. (2015). Connectomics-based analysis of information flow in the *Drosophila* brain. *Curr Biol* 25(10):1249–1258. doi:10.1016/j.cub.2015.03.021
- Stürner T, et al. (2025). Comparative connectomics of *Drosophila* descending and ascending neurons. *Nature* 643(8070):158–172. doi:10.1038/s41586-025-08925-z
- Sulyok B, Balogh SG, Palla G (2026). Network geometry of the Drosophila brain. arXiv:2602.16417
- Towlson EK, Vértes PE, Ahnert SE, Schafer WR, Bullmore ET (2013). The rich club of the *C. elegans* neuronal connectome. *J Neurosci* 33(15):6380–6387. doi:10.1523/JNEUROSCI.3784-12.2013
- van den Heuvel MP, Sporns O (2011). Rich-club organization of the human connectome. *J Neurosci* 31(44):15775–15786. doi:10.1523/JNEUROSCI.3539-11.2011
- van den Heuvel MP, Kahn RS, Goñi J, Sporns O (2012). High-cost, high-capacity backbone for global brain communication. *PNAS* 109(28):11372–11377. doi:10.1073/pnas.1203593109
- Worrell JC, Rumschlag J, Betzel RF, Sporns O, Mišić B (2017). Optimized connectome architecture for sensory-motor integration. *Netw Neurosci* 1(4):415–430. doi:10.1162/NETN_a_00022

### Methods, software and data sources cited in the report

Citation details for these were confirmed against Crossref or arXiv. They are cited in the report for the methods, software and datasets it uses, and were not reviewed as prior art.

- Alstott J, Bullmore E, Plenz D (2014). powerlaw: a Python package for analysis of heavy-tailed distributions. *PLoS ONE* 9(1):e85777. doi:10.1371/journal.pone.0085777
- Clauset A, Shalizi CR, Newman MEJ (2009). Power-law distributions in empirical data. *SIAM Review* 51(4):661–703. doi:10.1137/070710111
- Dorkenwald S, Matsliah A, Sterling AR, et al. (2024). Neuronal wiring diagram of an adult brain. *Nature* 634:124–138. doi:10.1038/s41586-024-07558-y
- Ford LR, Fulkerson DR (1956). Maximal flow through a network. *Canadian Journal of Mathematics* 8:399–404. doi:10.4153/CJM-1956-045-5
- Menger K (1927). Zur allgemeinen Kurventheorie. *Fundamenta Mathematicae* 10:96–115. doi:10.4064/fm-10-1-96-115
- Pedregosa F, Varoquaux G, Gramfort A, et al. (2011). Scikit-learn: machine learning in Python. *Journal of Machine Learning Research* 12:2825–2830. arXiv:1201.0490
- Plaza SM, Clements J, Dolafi T, et al. (2022). neuPrint: an open access tool for EM connectomics. *Frontiers in Neuroinformatics* 16:896292. doi:10.3389/fninf.2022.896292
- Schlegel P, Yin Y, Bates AS, et al. (2024). Whole-brain annotation and multi-connectome cell typing of *Drosophila*. *Nature* 634:139–152. doi:10.1038/s41586-024-07686-5
- Takemura S, Hayworth KJ, Huang GB, et al. (2024). A connectome of the male *Drosophila* ventral nerve cord. *eLife* 13:RP97769. doi:10.7554/eLife.97769
- Vuong QH (1989). Likelihood ratio tests for model selection and non-nested hypotheses. *Econometrica* 57(2):307–333. doi:10.2307/1912557
