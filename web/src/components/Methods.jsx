import CableLength, { CableTable } from "./figures/CableLength.jsx";
import { Figure, HeadingLevel, More, Outcome } from "./ui.jsx";
import { blobUrl, repoUrl, reportUrl } from "../lib/data.js";
import { count, fixed } from "../lib/format.js";
import "../styles/methods.css";

const PROTOCOL = [
  ["node", "cell type by side: soma hemisphere, or nerve-root hemisphere without a CNS soma"],
  ["edge threshold", "at least 1% of the target node's input synapses from typed neurons; self-loops dropped"],
  ["compartment", "brain-dominant if most synapses in CentralBrain, Optic(L), Optic(R) rather than VNC"],
  ["connective set", "majority superclass descending_neuron or ascending_neuron: 951 and 1,096 nodes"],
  ["placement null", "1000 uniform permutations of positions; within-compartment and subgraph variants"],
  ["swap search", "2,000,000 proposals between soma-placed nodes of one compartment, greedy"],
  ["rich-club null", "1000 rewirings of each connective layer, 10 swaps per edge, no multi-edges"],
  ["value null", "1000 random non-connective sets matched on total length, each within 0.01%"],
  ["generative sampling", "all edges and 2,454,420 uniform non-edges; 5-fold cross-validated AUC"],
  ["synthetic graphs", "50 per model, independent Bernoulli draws with a shift fixing the expected edge count"],
  ["empirical p", "(1 + null values at least as extreme) / (1 + N), one-sided, α = 0.05"],
  ["seeds", "base 20260916 plus a fixed offset per analysis, set in each module"],
];

const SOFTWARE = [
  ["Python", "3.12.12"],
  ["neuprint-python", "0.6.3"],
  ["igraph", "1.0.0"],
  ["NumPy / SciPy / pandas", "2.5.3 / 1.18.1 / 3.0.5"],
  ["scikit-learn", "1.9.1"],
  ["navis", "1.12.0"],
  ["powerlaw", "2.0.0"],
  ["trimesh", "5.1.0"],
  ["matplotlib / fontTools", "3.11.2 / 4.65.0"],
  ["pandoc / typst", "3.11 / 0.15.1"],
];

const FILES = [
  ["results/preregistration.md", "every hypothesis, the commit it was registered in, and its outcome"],
  ["results/spatial_optimality.md", "placement against 1000 permutations"],
  ["results/wiring_economy_extensions.md", "distance dependence, swaps, where the wire goes, length and traffic"],
  ["results/connective_richclub.md", "rich-club routing, partner enrichment and hubs"],
  ["results/connective_value.md", "the value of the connective against cost-matched wiring"],
  ["results/connective_price.csv", "price and value of every descending and ascending cell type"],
  ["results/generative_model.md", "the logistic wiring models and their synthetic graphs"],
  ["results/threshold_robustness.md", "the headline tests at three other edge thresholds"],
  ["results/wire_atlas.md", "the wire held by each neuropil and how economically each is wired inside"],
  ["results/wire_concentration.md", "how unevenly the budget is spread over connections and over cell classes"],
  ["results/prior_art.md", "the prior work checked before any claim was made"],
  ["paper/report.md", "the technical report"],
];

const LIMITS = [
  [
    "Resolution.",
    "The graph is aggregated to cell types by side, each placed at the centroid of its cell bodies. Within a class, soma-to-output distance does not predict a neuron's cable length, so positions capture differences between classes, not the cable of individual neurons.",
  ],
  [
    "Cost measure.",
    "Straight-line distance between centroids stands in for real processes, which follow neuropil tracts.",
  ],
  [
    "Edge threshold.",
    "Every result uses a 1% input threshold. Placement and hub results hold from 0.5% to 5%; rich-to-rich routing does not hold at 0.5%.",
  ],
  [
    "The connective set.",
    "It is defined by majority superclass. Sensory ascending neurons also pass through the neck but are treated as sensory inputs, so their wiring is not in the removed set.",
  ],
  [
    "Value measure.",
    "Flow capacity counts unweighted disjoint paths, so it rewards many short connections over fewer long ones. The count-matched and longest-connection comparisons are reported alongside the length-matched one for that reason.",
  ],
  [
    "Swap search.",
    "Greedy, stopped before convergence, and blind to the physical constraints on where neuropils and cell bodies can lie.",
  ],
  ["Generative models.", "Both draw each pair independently, so neither can produce reciprocity or clustering."],
  ["One animal.", "A single male fly and one static reconstruction."],
  ["Review.", "None of this has been peer reviewed."],
];

const REFERENCES = [
  "Berg S, et al. (2026). Sexual dimorphism in the complete Drosophila male central nervous system connectome. Cell 189(18):5504-5526.e15. doi:10.1016/j.cell.2026.08.015",
  "Cherniak C (1994). Component placement optimization in the brain. J Neurosci 14(4):2418-2427. doi:10.1523/JNEUROSCI.14-04-02418.1994",
  "Chen BL, Hall DH, Chklovskii DB (2006). Wiring optimization can relate neuronal structure and function. PNAS 103(12):4723-4728. doi:10.1073/pnas.0506806103",
  "Kaiser M, Hilgetag CC (2006). Nonoptimal component placement, but short processing paths, due to long-distance projections in neural systems. PLoS Comput Biol 2(7):e95. doi:10.1371/journal.pcbi.0020095",
  "van den Heuvel MP, Kahn RS, Goñi J, Sporns O (2012). High-cost, high-capacity backbone for global brain communication. PNAS 109(28):11372-11377. doi:10.1073/pnas.1203593109",
  "Towlson EK, Vértes PE, Ahnert SE, Schafer WR, Bullmore ET (2013). The rich club of the C. elegans neuronal connectome. J Neurosci 33(15):6380-6387. doi:10.1523/JNEUROSCI.3784-12.2013",
  "Lin A, et al. (2024). Network statistics of the whole-brain connectome of Drosophila. Nature 634(8032):153-165. doi:10.1038/s41586-024-07968-y",
  "Salova A, Kovács IA (2025). Combined topological and spatial constraints are required to capture the structure of neural connectomes. Netw Neurosci 9(1):181-206. doi:10.1162/netn_a_00428",
];

function Caution() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <path d="M8 1.8 15 14.2H1z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M8 6v3.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="8" cy="11.8" r="0.9" fill="currentColor" />
    </svg>
  );
}

export default function Methods({ data }) {
  const unsupported = data.hypotheses.filter((hypothesis) => !hypothesis.supported);
  const sets = data.value.sets;

  return (
    <section className="section" id="methods" aria-labelledby="methods-title">
      <div className="wrap">
        <HeadingLevel level={3}>
          <div className="section-head">
            <h2 id="methods-title">Methods and what they cannot show</h2>
            <p className="lede">
              Every hypothesis on this page was written down, with its direction, statistic, null model and
              threshold, before it was computed. Four of the thirteen are not supported, and they are reported here
              at the same size as the rest.
            </p>
          </div>

          <div className="callout">
            <p className="callout-title">
              <Caution />
              What these results are not
            </p>
            <p>
              These are structural results on a static wiring diagram aggregated to cell types. Wiring cost is the
              straight-line distance between cell-type positions, not the length of real neuronal processes, and flow
              capacity counts disjoint paths, not information transmitted or behaviour. Nothing here simulates neural
              activity or says how the nervous system develops.
            </p>
          </div>

          <div className="block">
            <h3 className="block-title">The thirteen pre-registered hypotheses</h3>
            <div className="table-wrap">
              <table className="data">
                <caption>
                  Registered in commits {data.preregistration_commits.join(", ")} before any result was computed. The
                  full index, with each hypothesis as it was written, is in{" "}
                  <a href={blobUrl("results/preregistration.md")}>results/preregistration.md</a>. The wire atlas and
                  the concentration of the budget carry no registered hypothesis: both were run after these tests
                  and are reported as description.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Hypothesis</th>
                    <th scope="col">Statement</th>
                    <th scope="col">Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {data.hypotheses.map((hypothesis) => (
                    <tr key={hypothesis.label}>
                      <th scope="row">{hypothesis.label}</th>
                      <td>{hypothesis.statement}</td>
                      <td>
                        <Outcome supported={hypothesis.supported} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="caption">
              {unsupported.length} of {data.hypotheses.length} are not supported:{" "}
              {unsupported.map((hypothesis) => hypothesis.label).join(", ")}. Cutting the neck costs less flow than
              random wiring of equal length, not more. Wire length does not predict a connective type&rsquo;s flow
              once its number of connections is known, in either direction. And the rich-to-rich route result does
              not survive a lower edge threshold, so the robustness hypothesis fails.
            </p>
          </div>

          <div className="block">
            <h3 className="block-title">How it was done</h3>
            <ol className="steps">
              <li>
                <div>
                  <h4>Data</h4>
                  <p>
                    The male CNS connectome, <code>male-cns:v1.0</code>, queried through neuPrint.{" "}
                    {count(data.graph.typed_neurons)} neurons carry a cell type.
                  </p>
                </div>
              </li>
              <li>
                <div>
                  <h4>Spatial graph</h4>
                  <p>
                    Each node is a cell type on one side of the body, at the centroid of its neurons&rsquo; cell
                    bodies, or of their synapses for the nodes, mostly sensory, whose cell bodies lie outside the
                    CNS. A connection is kept when it supplies at least 1% of the target&rsquo;s input synapses from
                    typed neurons. That gives {count(data.graph.spatial_graph.nodes)} nodes and{" "}
                    {count(data.graph.spatial_graph.edges)} connections. Pooled across sides, the same rule gives
                    exactly the {count(data.graph.type_graph.types)}-type graph of ConnectomeLens and Fault Lines.
                  </p>
                  <code className="formula">w(u → v) / Σ w(u&apos; → v) ≥ 0.01</code>
                </div>
              </li>
              <li>
                <div>
                  <h4>Pre-registration</h4>
                  <p>
                    Every hypothesis was committed before it was computed, in{" "}
                    {data.preregistration_commits.join(", ")}. Each results file keeps that section unchanged and the
                    scripts append beneath it.
                  </p>
                </div>
              </li>
              <li>
                <div>
                  <h4>Wiring cost and placement</h4>
                  <p>
                    The cost of a set of connections is the sum of the distances between the positions of their
                    endpoints. The real cost is compared with 1000 permutations of the positions over the nodes, with
                    a one-sided empirical p-value. The swap search proposes {count(data.swaps.proposals)} exchanges
                    of position within a compartment and keeps each one that lowers the cost.
                  </p>
                  <code className="formula">C = Σ ‖x(u) − x(v)‖&nbsp;&nbsp;&nbsp;p = (1 + #{"{i : C(πᵢ) ≤ C}"}) / 1001</code>
                </div>
              </li>
              <li>
                <div>
                  <h4>Rich club</h4>
                  <p>
                    A partner&rsquo;s richness is its degree among non-connective types; the top 10% of brain and of
                    nerve-cord partners are rich. The route count sums, over connective types, the rich partners on
                    one side times the rich partners on the other. Each of the four layers of connective connections
                    is rewired 1000 times by degree-preserving swaps.
                  </p>
                  <code className="formula">R = Σ r_in(c) · r_out(c)</code>
                </div>
              </li>
              <li>
                <div>
                  <h4>Value</h4>
                  <p>
                    Flow capacity is a unit-capacity maximum flow from a supersource feeding {count(sets.sensory)}{" "}
                    sensory nodes to a supersink drained by {count(sets.motor)} motor nodes, the Fault Lines
                    implementation copied unchanged. The neck-crossing connections are compared with 1000 random sets
                    of non-connective connections matched on total length, 1000 matched on count, and the longest
                    non-connective connections of the same length.
                  </p>
                </div>
              </li>
              <li>
                <div>
                  <h4>Generative model</h4>
                  <p>
                    Logistic regression of edge presence on distance, its logarithm, a shared compartment and the
                    ordered pair of superclasses, fitted on all connections and five sampled non-connections per
                    connection, with the intercept corrected for sampling.{" "}
                    {data.generative.comparison.n_synthetic} synthetic graphs per model are drawn with the expected
                    connection count fixed to the real one.
                  </p>
                </div>
              </li>
              <li>
                <div>
                  <h4>Checks</h4>
                  <p>
                    The placement, route and hub tests are repeated at edge thresholds of 0.5%, 2% and 5%.{" "}
                    <code>make verify</code> recomputes every statistic from the saved nulls, regenerates every
                    report, and checks the headline numbers in the README and the paper against the result files.
                  </p>
                </div>
              </li>
            </ol>
          </div>

          <Figure
            title="Positions stand in for cable length between classes, not within them"
            caption={
              <>
                Skeleton cable length against soma-to-output distance for {count(data.cable.analysed)} neurons
                sampled from four classes, both axes logarithmic; the two connective classes are drawn in the wire
                colour. Pooled across classes the two are correlated (ρ = {fixed(data.cable.spearman_rho, 3)});
                within each class the correlation is near zero. This is the check behind the first limitation below.
              </>
            }
          >
            <CableLength data={data} />
            <More summary="Values behind the cable-length check">
              <CableTable data={data} />
            </More>
          </Figure>

          <div className="block">
            <h3 className="block-title">Where it falls short</h3>
            <ul className="limits">
              {LIMITS.map(([lead, text]) => (
                <li key={lead}>
                  <strong>{lead}</strong> {text}
                </li>
              ))}
            </ul>
          </div>

          <div className="block">
            <h3 className="block-title">Settings, software and files</h3>
            <More summary="Protocol settings">
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th scope="col">Setting</th>
                      <th scope="col">Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {PROTOCOL.map(([setting, value]) => (
                      <tr key={setting}>
                        <th scope="row">{setting}</th>
                        <td>{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </More>
            <More summary="Software">
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th scope="col">Package</th>
                      <th scope="col" className="num-col">
                        Version
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {SOFTWARE.map(([name, version]) => (
                      <tr key={name}>
                        <th scope="row">{name}</th>
                        <td className="num-col">{version}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </More>
            <More summary="Every number on this page, in the repository">
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th scope="col">File</th>
                      <th scope="col">What it holds</th>
                    </tr>
                  </thead>
                  <tbody>
                    {FILES.map(([path, description]) => (
                      <tr key={path}>
                        <th scope="row">
                          <a href={blobUrl(path)}>{path}</a>
                        </th>
                        <td>{description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </More>
            <More summary="Reproduce every result">
              <pre className="cmd">
                {"python -m venv .venv && . .venv/bin/activate\npip install -r requirements.txt\nmake reproduce"}
              </pre>
              <p className="caption">
                Requirements: Python 3.12, GNU Make, and network access to neuPrint and the public flyem-male-cns
                bucket. Raw data are cached under <code>data/</code> and are not committed. All randomness is seeded
                from 20260916. The stages also run on their own: <code>make data</code>, <code>make analyze</code>,{" "}
                <code>make hero</code>, <code>make readme</code>, <code>make poster</code>, <code>make paper</code>,{" "}
                <code>make export</code>, <code>make test</code> and <code>make verify</code>.
              </p>
            </More>
          </div>

          <div className="block">
            <h3 className="block-title">References</h3>
            <ul className="refs">
              {REFERENCES.map((reference) => {
                const doi = reference.match(/doi:(\S+)/)[1];
                const [text] = reference.split(" doi:");
                return (
                  <li key={doi}>
                    {text} <a href={`https://doi.org/${doi}`}>doi:{doi}</a>
                  </li>
                );
              })}
              <li>
                Sarkar D (2026). Fault Lines: attack tolerance and structural robustness of the complete{" "}
                <i>Drosophila</i> male CNS connectome.{" "}
                <a href="https://github.com/dhruvin-sarkar/fault-lines">github.com/dhruvin-sarkar/fault-lines</a>
              </li>
            </ul>
            <p className="caption">
              Every claim on this page was checked against the prior work listed in{" "}
              <a href={blobUrl("results/prior_art.md")}>results/prior_art.md</a> before it was made. The full
              treatment, with the derivations and the complete reference list, is in{" "}
              <a href={reportUrl}>the technical report</a>.
            </p>
          </div>
        </HeadingLevel>
      </div>
    </section>
  );
}

export function Footer({ data }) {
  return (
    <footer className="footer">
      <div className="wrap">
        <div className="footer-grid">
          <div>
            <p className="footer-title">The Price of Thought</p>
            <p>
              Wiring economy of the complete <i>Drosophila</i> male CNS connectome. An independent, pre-registered
              analysis of public data by Dhruvin Sarkar. Not peer reviewed.
            </p>
          </div>
          <div>
            <p className="footer-heading">This study</p>
            <ul>
              <li>
                <a href={reportUrl}>Technical report (PDF)</a>
              </li>
              <li>
                <a href={blobUrl("results/preregistration.md")}>Pre-registration</a>
              </li>
              <li>
                <a href={blobUrl("assets/readme/price-of-thought-poster.png")}>One-page poster</a>
              </li>
              <li>
                <a href={repoUrl}>Code and result files</a>
              </li>
            </ul>
          </div>
          <div>
            <p className="footer-heading">A three-part study</p>
            <ul>
              <li>
                <a href="https://github.com/dhruvin-sarkar/ConnectomeLens">ConnectomeLens</a>: does the male wiring
                alone identify the sexually dimorphic cell types?
              </li>
              <li>
                <a href="https://github.com/dhruvin-sarkar/fault-lines">Fault Lines</a>: how much can be removed
                before sensory input no longer reaches motor output?
              </li>
              <li>The Price of Thought: what does the wiring cost, and what does its most expensive part buy?</li>
            </ul>
          </div>
        </div>
        <p className="footer-note">
          Data: the male adult <i>Drosophila</i> CNS connectome from HHMI Janelia FlyEM and Google Research, released
          under CC-BY 4.0 (Berg et al., <i>Cell</i> 2026), accessed through{" "}
          <a href="https://neuprint.janelia.org">neuPrint</a>, with neuropil meshes from the public flyem-male-cns
          bucket. {count(data.graph.typed_neurons)} typed neurons, {count(data.graph.spatial_graph.nodes)} cell types
          by side, {count(data.graph.spatial_graph.edges)} connections. Code released under the{" "}
          <a href={blobUrl("LICENSE")}>MIT License</a>; citation metadata in{" "}
          <a href={blobUrl("CITATION.cff")}>CITATION.cff</a>.
        </p>
      </div>
    </footer>
  );
}
