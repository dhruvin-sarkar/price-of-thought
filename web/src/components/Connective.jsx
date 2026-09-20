import CostShare, { CostShareTable } from "./figures/CostShare.jsx";
import Lookup from "./Lookup.jsx";
import PriceValue, { PriceTestsTable } from "./figures/PriceValue.jsx";
import RichClub, { RichClubTable } from "./figures/RichClub.jsx";
import ValueNulls, { ValueTable } from "./figures/ValueNulls.jsx";
import { Figure, HeadingLevel, Keynote, More, Sidenote, TextBlock } from "./ui.jsx";
import { count, fixed, micron, percent, times } from "../lib/format.js";
import { headline } from "../lib/headline.js";

export default function Connective({ data }) {
  const h = headline(data);
  const membership = data.richclub.membership;
  const routes = data.richclub.routes.total;
  const descending = data.price.tests.descending;
  const meanLength = data.swaps.start_cost / data.graph.spatial_graph.edges;

  return (
    <section className="section" id="connective" aria-labelledby="connective-title">
      <div className="wrap">
        <HeadingLevel level={3}>
          <div className="section-head">
            <h2 id="connective-title">The connective is the expensive part</h2>
            <p className="lede">
              A few thousand connections run the length of the animal, between the brain and the nerve cord. Here is
              what they cost, and what the nervous system gets for them.
            </p>
          </div>

          <TextBlock
            notes={[
              <Keynote key="share" value={percent(h.neck.cost_share)}>
                of all wiring length, in the {percent(h.neck.edge_share)} of connections that cross the neck
              </Keynote>,
              <Sidenote key="mean" title="Three times the mean">
                A neck-crossing connection runs {micron(h.neck.mean_length_um)} on average, against{" "}
                {micron(meanLength, 1)} for all connections.
              </Sidenote>,
              <Sidenote key="hubs" title="Hub connections are longer too">
                Connections touching a cell type in the top tenth by degree average {micron(h.meanHigh)} against{" "}
                {micron(h.meanOther)} for the rest.
              </Sidenote>,
            ]}
          >
            <p>
              A neck-crossing connection joins a descending or ascending cell type to a partner on the far side of
              the neck. There are {count(h.neck.edges)} of them. They are under a tenth of the connections in the
              graph and they hold nearly a quarter of its wire.
            </p>
            <p>
              This is the pattern described as a high-cost, high-capacity backbone in the human and{" "}
              <i>C. elegans</i> connectomes: a small set of long connections between well-connected regions, carrying
              a disproportionate share of communication. The first half of that description holds here. The second
              half is what the rest of this section tests.
            </p>
          </TextBlock>

          <Figure
            number={3}
            title="The neck holds a quarter of the wire in under a tenth of the connections"
            caption={
              <>
                Share of all connections and share of total wiring length, for four groups. The first three overlap;
                the last holds the connections in none of them. Longer connections also lie on somewhat more shortest
                paths (Spearman ρ = {fixed(data.length_traffic.rho_all, 3)} between length and edge betweenness).
              </>
            }
          >
            <CostShare data={data} />
            <More summary="Values behind Figure 3">
              <CostShareTable data={data} />
            </More>
          </Figure>

          <TextBlock
            notes={[
              <Keynote key="odds" value={fixed(h.odds, 2)}>
                the odds that a connective cell type is a hub, against other cell types
              </Keynote>,
              <Sidenote key="partners" title="Rich partners">
                The partners of connective types are enriched for well-connected types, {times(h.enrichment, 2)} a
                uniform redraw.
              </Sidenote>,
              <Sidenote key="fragile" title="Where it breaks">
                The route excess comes entirely from ascending routes, depends on where the line for
                &ldquo;rich&rdquo; is drawn, and disappears when connections carrying 0.5% of a target&rsquo;s input
                are counted.
              </Sidenote>,
            ]}
          >
            <p>
              A rich-club organization is one in which well-connected nodes are more densely interconnected than
              their degrees alone predict. Lin and colleagues expected descending and ascending neurons to join a
              rich club spanning the whole nervous system, and noted that testing it needed a complete CNS
              connectome. This is that test.
            </p>
            <p>
              Connective cell types are over-represented among hubs: {percent(membership.descending_share_high)} of
              descending and {percent(membership.ascending_share_high)} of ascending types are in the top tenth by
              degree, against {percent(membership.other_share_high)} of the rest. The route statistic counts two-step
              paths from a rich partner on one side, through a connective type, to a rich partner on the other:{" "}
              {count(routes.real)} real routes against {count(routes.null_mean)} ± {count(routes.null_sd)} in 1000
              rewirings that keep every degree in each layer.
            </p>
            <p>
              The excess is real but modest, and it is fragile. Move the line for a rich partner, or count the weaker
              connections that a 0.5% threshold admits, and it goes away.
            </p>
          </TextBlock>

          <Figure
            number={4}
            title="The connective favours well-connected partners, but its rich-to-rich routing is modest and fragile"
            caption={
              <>
                Ratio of real rich-to-rich routes through the connective to the mean of 1000 layer-preserving
                rewirings. The pale band is the central 95% of those rewirings; a filled point lies outside it at
                p ≤ 0.05, a hollow point does not. Above: the share of partners on each side counted as rich. Below:
                the edge threshold used to build the whole graph.
              </>
            }
          >
            <RichClub data={data} />
            <More summary="Values behind Figure 4">
              <RichClubTable data={data} />
            </More>
          </Figure>

          <TextBlock
            notes={[
              <Keynote key="flow" value={times(h.flowRatio, 2)}>
                the sensory-to-motor flow that random wiring of the same total length removes
              </Keynote>,
              <Sidenote key="direction" title="Except downward">
                Cutting the neck removes{" "}
                {percent(
                  data.value.families.crossing_cost.flow_brain_to_vnc.real / data.value.intact.flow_brain_to_vnc,
                  0,
                )}{" "}
                of the flow from brain sensory to nerve-cord motor types, {times(h.brainRatio, 2)} the random loss.
              </Sidenote>,
              <Sidenote key="count" title="Per connection, more">
                Against an equal number of random connections rather than an equal length, the neck carries{" "}
                {times(data.value.families.crossing_count.flow.ratio, 2)} as much.
              </Sidenote>,
            ]}
          >
            <p>
              Flow capacity is the number of edge-disjoint paths from sensory to motor cell types, the measure used
              in Fault Lines. The intact graph supports {count(data.value.intact.flow)}. The question is whether the
              neck, for what it costs, carries more of that routing than ordinary wiring of the same total length
              would.
            </p>
            <p>
              It does not. Cutting the {count(h.neck.edges)} neck-crossing connections removes{" "}
              {count(data.value.families.crossing_cost.flow.real)} units; 1000 random sets of ordinary connections of
              the same total length remove {count(data.value.families.crossing_cost.flow.null_mean)} on average.
              Against the longest ordinary connections of the same total length it carries the same. This
              pre-registered hypothesis is not supported.
            </p>
            <p>
              Its distinctive contribution is directional. The neck is the route by which what the brain senses
              reaches the muscles, and cutting it takes out far more of that than random wiring does.
            </p>
          </TextBlock>

          <Figure
            number={5}
            title="Per unit of wire, the neck carries less routing than ordinary wiring, except from brain to nerve cord"
            caption={
              <>
                Each histogram is the flow capacity removed by 1000 random sets of ordinary connections matched to
                the neck on total length. The orange rule is the loss from cutting the neck itself. In the first
                panel the dashed rules mark two other comparisons: an equal number of random connections, and the
                longest ordinary connections of the same total length.
              </>
            }
          >
            <ValueNulls data={data} />
            <More summary="Values behind Figure 5">
              <ValueTable data={data} />
            </More>
          </Figure>

          <Figure
            number={6}
            title="More wire does not buy a cell type more flow"
            caption={
              <>
                For each descending or ascending cell type on one side, its price is the total length of its
                neck-crossing connections and its value the flow lost, in its own direction, when they alone are
                removed. Most types can be removed at no cost to flow. Among descending types price and value are
                correlated (ρ = {fixed(descending.spearman_rho, 3)}), but at a given number of connections longer
                wiring buys nothing more (partial ρ = {fixed(descending.partial_rho, 3)}); among ascending types they
                are unrelated. Hover a point for its cell type.
              </>
            }
          >
            <PriceValue data={data} />
            <More summary="Values behind Figure 6">
              <PriceTestsTable data={data} />
            </More>
          </Figure>

          <Figure
            id="lookup"
            title="Every connective cell type, with what its wiring costs and what it carries"
            caption="Sort by any column, or search for a cell type by name. Price is the summed straight-line length of a type's neck-crossing connections."
          >
            <Lookup data={data} />
          </Figure>
        </HeadingLevel>
      </div>
    </section>
  );
}
