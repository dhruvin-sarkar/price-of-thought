import DistanceCurves, { DistanceTable } from "./figures/DistanceCurves.jsx";
import PlacementTests, { PlacementTable } from "./figures/PlacementTests.jsx";
import { Figure, HeadingLevel, Keynote, More, Sidenote, TextBlock } from "./ui.jsx";
import { blobUrl } from "../lib/data.js";
import { count, fixed, micron, percent } from "../lib/format.js";
import { headline } from "../lib/headline.js";

export default function Placement({ data }) {
  const h = headline(data);
  const minima = data.distance.minima;

  return (
    <section className="section" id="placement" aria-labelledby="placement-title">
      <div className="wrap">
        <HeadingLevel level={3}>
          <div className="section-head">
            <h2 id="placement-title">Cell types sit where their wiring is short</h2>
            <p className="lede">
              Keep the graph and the set of positions, and shuffle only which cell type sits where. Do it a thousand
              times, and the real layout is cheaper than every one of them.
            </p>
          </div>

          <TextBlock
            notes={[
              <Keynote key="ratio" value={fixed(h.ratio, 3)}>
                the wire of the mean random placement, over {count(data.graph.spatial_graph.edges)} connections
                between {count(data.graph.spatial_graph.nodes)} cell types by side
              </Keynote>,
              <Sidenote key="within" title="Not just brain and cord">
                The full shuffle moves brain types into the nerve cord, which is an easy null to beat. Shuffling only
                within a compartment still leaves the real layout {percent(1 - h.withinRatio, 0)} cheaper.
              </Sidenote>,
              <Sidenote key="swaps" title="Far from optimal">
                Greedy swaps between two cell types of one compartment, each kept only if it shortens the wire, cut a
                further {percent(h.swap)}. The search stopped before it converged, so that is a lower bound.
              </Sidenote>,
            ]}
          >
            <p>
              Wiring cost here is the summed straight-line distance between the positions of connected cell types,
              the measure Cherniak used for component placement in the brain. The test asks whether the arrangement
              we see is cheaper than the arrangements that were available to it.
            </p>
            <p>
              It is, by a wide margin, in every variant: weighting each connection by its synapses, placing types at
              their synapse centroids instead of their cell bodies, and restricting the shuffle to the brain or to
              the nerve cord alone. No permutation in any test came within reach of the real value.
            </p>
            <p>
              It is also not the cheapest arrangement available. Swapping positions between pairs of cell types in
              the same compartment finds at least a third more to save. As in <i>C. elegans</i>, the layout is far
              cheaper than random and far from optimal; long connections that shorten processing paths are the kind
              that keep a layout from its optimum.
            </p>
          </TextBlock>

          <Figure
            number={1}
            title="The real placement is less than half as costly as random placement, and a third more costly than it needs to be"
            caption={
              <>
                Each test keeps the graph and the set of positions and shuffles only which cell type sits where, 1000
                times. Bars give the real cost as a share of the permuted mean, so 1.0 is random placement. The mark
                at {fixed(h.ratio * (1 - h.swap), 3)} is where cost-reducing swaps take the primary layout. Hover or
                focus a bar for its real cost, its permuted mean and its z-score.
              </>
            }
          >
            <PlacementTests data={data} />
            <More summary="Values behind Figure 1">
              <PlacementTable data={data} />
            </More>
          </Figure>

          <Figure
            number={2}
            title="Nearby cell types connect far more often, except at the longest distances"
            caption={
              <>
                Share of ordered cell-type pairs joined by a connection, in 20 µm bins holding at least 1000 pairs,
                on a logarithmic scale. Probability falls with distance across all pairs (Spearman ρ ={" "}
                {fixed(data.distance.summary.all.spearman_rho, 3)} over {data.distance.summary.all.bins} bins), with a
                length constant of {micron(h.lengthConstant)} over the first 600 µm. Inside the brain and inside the
                nerve cord the fall is not monotonic: probability reaches a minimum at{" "}
                {micron(minima["brain-brain"].minimum_bin_um)} and {micron(minima["vnc-vnc"].minimum_bin_um)}, then
                rises again, because most of the longest connections join a cell type on one side of the body to one
                on the other.
              </>
            }
          >
            <DistanceCurves data={data} />
            <More summary="Values behind Figure 2">
              <DistanceTable data={data} />
              <p className="caption">
                Per-bin pair and edge counts are in{" "}
                <a href={blobUrl("results/distance_dependence.csv")}>results/distance_dependence.csv</a>.
              </p>
            </More>
          </Figure>
        </HeadingLevel>
      </div>
    </section>
  );
}
