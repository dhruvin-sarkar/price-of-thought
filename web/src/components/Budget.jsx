import Lorenz, { TailTable } from "./figures/Lorenz.jsx";
import RegionEconomy, { EconomyTable, tested } from "./figures/RegionEconomy.jsx";
import Superclasses, { SuperclassTable } from "./figures/Superclasses.jsx";
import WireAtlas, { AtlasTable, ranked } from "./figures/WireAtlas.jsx";
import { Figure, HeadingLevel, Keynote, More, Sidenote, TextBlock } from "./ui.jsx";
import { count, fixed, micron, percent, superclassName } from "../lib/format.js";

const metres = (um) => `${fixed(um / 1e6, 1)} m`;

export default function Budget({ data }) {
  const { neuropils, pairs, totals } = data.atlas;
  const { lorenz, lengths, tail, superclasses } = data.concentration;
  const largest = neuropils[0];
  const shown = ranked(data);
  const inTop = shown.reduce((sum, row) => sum + row.wire_share, 0);
  const regions = tested(data);
  const loose = regions.filter((row) => row.n_at_or_below_real > totals.permutations * 0.05);
  const thrifty = regions.reduce((best, row) => (row.cost_ratio < best.cost_ratio ? row : best));
  const whole = lorenz.all;
  const neck = lorenz["across the neck"];
  const owner = superclasses[0];

  return (
    <section className="section" id="budget" aria-labelledby="budget-title">
      <div className="wrap">
        <HeadingLevel level={3}>
          <div className="section-head">
            <h2 id="budget-title">The budget is spent between regions, not inside them</h2>
            <p className="lede">
              Hand every connection to the neuropils nearest its two ends. One region takes a tenth of all the wire
              in the animal, and only a sixteenth of the budget stays inside any single region at all.
            </p>
          </div>

          <TextBlock
            notes={[
              <Keynote key="largest" value={percent(largest.wire_share)}>
                of all wire ends in the {largest.neuropil}, the largest share of the{" "}
                {count(totals.neuropils_with_types)} neuropils that hold any
              </Keynote>,
              <Sidenote key="within" title="Between, not within">
                Only {percent(totals.share_within_one_neuropil)} of the wire runs between two cell types nearest the
                same neuropil. The rest of the {metres(totals.total_wire_um)} crosses from one region to another.
              </Sidenote>,
              <Sidenote key="exception" title="Three regions show no saving">
                {loose.map((row) => row.neuropil).join(", ")} are not reliably cheaper than reshuffling their own
                cell types among their own positions. The two antennal lobes are the largest of that group.
              </Sidenote>,
            ]}
          >
            <p>
              A cell type is assigned to the neuropil whose surface lies nearest its position, and each connection
              lends half its length to the neuropil at each of its ends. That splits the{" "}
              {metres(totals.total_wire_um)} of wire in the graph across {count(totals.neuropils_with_types)}{" "}
              regions, and asks which of them the animal is paying for.
            </p>
            <p>
              The answer is concentrated. The {shown.length} regions in the figure below hold {percent(inTop)} of
              the budget between them, led by the gnathal ganglion at {percent(largest.wire_share)} and the
              abdominal neuromere at {percent(neuropils[1].wire_share)}. The most expensive pair of regions is{" "}
              {pairs[0].a} to {pairs[0].b}, carrying {metres(pairs[0].wire_um)} over {count(pairs[0].edges)}{" "}
              connections.
            </p>
            <p>
              The permutation test applied to the whole animal can be applied inside one region: keep that
              region&rsquo;s own positions, and shuffle only which of its cell types sits where. Of the{" "}
              {count(regions.length)} regions large enough to test, {count(regions.length - loose.length)} are
              cheaper than at least {percent(0.95, 0)} of their own reshuffles, most economically {thrifty.neuropil}{" "}
              at {fixed(thrifty.cost_ratio, 3)}. The exceptions matter as much as the rule. The antennal lobes,
              whose glomeruli are the textbook case of an orderly wiring plan, are no cheaper than chance on this
              measure: their order is not an order that shortens wire.
            </p>
          </TextBlock>

          <Figure
            number={3}
            title="A tenth of all the wire ends in one region, and more than half of it in fourteen"
            caption={
              <>
                Share of the {metres(totals.total_wire_um)} wiring budget held by each of the {shown.length}{" "}
                neuropils holding the most, of {count(totals.neuropils_with_types)} that hold any. Each connection
                lends half its length to the neuropil nearest each of its ends. Brain regions are drawn in copper
                and nerve-cord regions in grey. Hover a bar for its wire, its cell types and its internal economy.
              </>
            }
          >
            <WireAtlas data={data} />
            <More summary="Values behind Figure 3">
              <AtlasTable data={data} />
            </More>
          </Figure>

          <Figure
            number={4}
            title="Almost every region is wired more cheaply than its own cells could be rearranged, and the antennal lobes are not"
            caption={
              <>
                Each point is one of the {count(regions.length)} neuropils with at least 12 cell types and 50
                connections of its own. Its height is the cost of its internal wiring as a share of the mean of{" "}
                {count(totals.permutations)} reshuffles of its own cell types among its own positions, so 1.0 is no
                better than chance. Economy does not follow size: the most economical region, {thrifty.neuropil} at{" "}
                {fixed(thrifty.cost_ratio, 3)}, holds {percent(thrifty.wire_share)} of the budget, while the two
                regions sitting closest to chance are among the largest in the brain.
              </>
            }
          >
            <RegionEconomy data={data} />
            <More summary="Values behind Figure 4">
              <EconomyTable data={data} />
            </More>
          </Figure>

          <TextBlock
            notes={[
              <Keynote key="gini" value={fixed(whole.gini, 3)}>
                the Gini coefficient of the budget over {count(whole.connections)} connections, where 0 spreads it
                evenly and 1 puts all of it on one
              </Keynote>,
              <Sidenote key="tail" title="Not a power law">
                The upper tail fits an exponent of {fixed(tail.alpha, 2)} above {micron(tail.xmin_um)}, but a
                lognormal and a truncated power law both describe it better. Long connections are expensive without
                being scale-free.
              </Sidenote>,
              <Sidenote key="neck" title="The neck is the even one">
                Neck-crossing connections have the most uniform budget of any set here, at a Gini of{" "}
                {fixed(neck.gini, 3)}, because there are no short ones among them.
              </Sidenote>,
            ]}
          >
            <p>
              The other way to ask where the budget goes is to ignore anatomy and rank the connections themselves.
              Sorted longest first, the top {percent(0.01, 0)} hold {percent(whole.top_shares["0.01"])} of the wire
              and the top {percent(0.1, 0)} hold {percent(whole.top_shares["0.1"])}. Half of them hold{" "}
              {percent(whole.top_shares["0.5"])}.
            </p>
            <p>
              That is uneven, but it is not the extreme concentration a few dominant long-range tracts would
              produce. A Gini of {fixed(whole.gini, 3)} describes a broad distribution with a heavy shoulder rather
              than a winner-take-all one, and the same holds inside the brain (
              {fixed(lorenz["within the brain"].gini, 3)}) and inside the nerve cord (
              {fixed(lorenz["within the nerve cord"].gini, 3)}). The cost of this nervous system is carried by very
              many moderately long connections, not by a handful of expensive ones.
            </p>
            <p>
              Split by the class of cell that owns them, the shares follow cell counts rather than distances.{" "}
              {superclassName(owner.superclass)} types touch {percent(owner.wire_share)} of the wire at a mean
              length of {micron(owner.mean_length_um)}, while the ascending and descending neurons that cross the
              neck touch far less of it at more than twice that mean.
            </p>
          </TextBlock>

          <Figure
            number={5}
            title="The longest tenth of connections hold under a third of the wire"
            caption={
              <>
                Cumulative share of the wiring budget against the cumulative share of connections, taken longest
                first, for all {count(lengths.all.edges)} connections and for three subsets. A budget spread evenly
                over its connections would follow the diagonal; the further a curve bows above it, the more of the
                cost sits on the longest few. Hover for the share each set has reached at that point.
              </>
            }
          >
            <Lorenz data={data} />
            <More summary="Values behind Figure 5">
              <TailTable data={data} />
            </More>
          </Figure>

          <Figure
            number={6}
            title="Central brain interneurons touch more than half the budget, at half the length of a neck crossing"
            caption={
              <>
                Share of the wiring budget on connections touching each class of cell. A connection between two
                classes counts for both, so the shares add to more than one. The ordering follows how many cells a
                class has rather than how far they reach: the classes with the longest mean connections sit well
                down the list. Hover a bar for its counts and its mean and median length.
              </>
            }
          >
            <Superclasses data={data} />
            <More summary="Values behind Figure 6">
              <SuperclassTable data={data} />
            </More>
          </Figure>
        </HeadingLevel>
      </div>
    </section>
  );
}
