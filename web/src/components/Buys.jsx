import { useState } from "react";
import Efficiency, { AXES, Component, ComponentTable, EfficiencyTable } from "./figures/Removal.jsx";
import SynapseValue, { SynapseTable } from "./figures/SynapseValue.jsx";
import { Figure, HeadingLevel, Keynote, More, Segmented, Sidenote, TextBlock, Unregistered } from "./ui.jsx";
import { count, fixed, micron, millimetre, percent, times } from "../lib/format.js";

const axisLabel = (value) => AXES.find((option) => option.value === value).label.toLowerCase();

export default function Buys({ data }) {
  const [axis, setAxis] = useState("wire");
  const { deciles, groups, totals } = data.synapses;
  const shortest = deciles[0];
  const longest = deciles[deciles.length - 1];
  const all = groups.all;
  const neck = groups["across the neck"];
  const elsewhere = groups.elsewhere;
  // What is left of the fall once the length is divided out of it.
  const belowRate = deciles.filter((row) => row.observed_over_expected < 1).length;
  const residual = shortest.observed_over_expected / longest.observed_over_expected;
  const { comparison, graph, baseline, sampling } = data.tradeoff;
  const at = comparison.at_reference;
  const perMetre = comparison.efficiency_lost_per_metre;
  const factor = perMetre["shortest first"] / perMetre["longest first"];
  // The last point of the curves, where the two measures have come furthest apart.
  const far = {
    long: data.tradeoff.curves["longest first"].at(-1),
    short: data.tradeoff.curves["shortest first"].at(-1),
  };

  return (
    <section className="section" id="buys" aria-labelledby="buys-title">
      <div className="wrap">
        <HeadingLevel level={3}>
          <div className="section-head">
            <h2 id="buys-title">What a micrometre of wire buys</h2>
            <p className="lede">
              The budget is spent. Two things it could be buying are synapses and connectivity. Measured against
              the length that paid for them, it buys the first at a flat rate and the second more cheaply at the
              short end than at the long one.
            </p>
          </div>

          <Unregistered>
            The two analyses below and the three in the next section were run after the thirteen registered
            hypotheses had been tested and the report written. None of them carries a registered hypothesis, none
            had a direction fixed in advance, and their p-values are uncorrected. Like the wire atlas and the
            concentration of the budget, they are reported as description and not as tests, and nothing in them
            changes a registered outcome.
          </Unregistered>

          <TextBlock
            notes={[
              <Keynote key="fall" value={times(1 / all.longest_over_shortest_per_um, 0)}>
                more synapses per micrometre in the shortest tenth of connections than in the longest, almost all
                of it the length in the denominator
              </Keynote>,
              <Sidenote key="median" title="The numerator is flat">
                The median connection carries {count(shortest.median_synapses)} synapses in the shortest decile
                and {count(longest.median_synapses)} in the longest, a ratio of{" "}
                {fixed(all.longest_over_shortest_median, 2)}.
              </Sidenote>,
              <Sidenote key="p" title="Why the p-values are useless here">
                At {count(all.edges)} connections a rank correlation of {fixed(all.correlation.spearman_rho, 3)}{" "}
                still returns a p-value at the floor of double precision. That is a statement about the number of
                connections, not about the size of the effect.
              </Sidenote>,
            ]}
          >
            <p>
              The {count(all.edges)} connections of the cell-type graph hold {millimetre(all.wire_um)} of wire and{" "}
              {count(all.synapses)} synapses between them, {fixed(all.synapses_per_um, 3)} synapses for every
              micrometre laid down. Sorting them by length into ten equal groups makes that rate look strongly
              dependent on length: the shortest tenth buys {fixed(shortest.synapses_per_um, 2)} synapses per
              micrometre and the longest {fixed(longest.synapses_per_um, 2)}, a factor of{" "}
              {fixed(1 / all.longest_over_shortest_per_um, 0)}.
            </p>
            <p>
              It is not. Synapses per micrometre is a ratio, and almost the whole of that fall is the denominator.
              The rank correlation between a connection&rsquo;s length and the number of synapses it carries is{" "}
              {fixed(all.correlation.spearman_rho, 3)} over every connection in the graph, and Pearson&rsquo;s r
              between the logarithms of the two is {fixed(all.correlation.pearson_log_r, 3)}. A long connection
              carries about the same number of synapses as a short one. The figure sets the observed rate against
              the rate each decile would show if synapse count did not depend on length at all, and the two curves
              are close enough that the decline is nearer arithmetic than discovery.
            </p>
            <p>
              Dividing the length back out leaves a residual, and that residual is the honest size of what is
              here. Against the rate each decile would show if synapse count did not depend on length at all, the
              shortest tenth buys at {fixed(shortest.observed_over_expected, 2)} times the going rate and the
              longest at {fixed(longest.observed_over_expected, 2)}, with the {count(belowRate)} longest deciles
              all below one. Between the two ends that is a factor of {fixed(residual, 1)}, against the{" "}
              {fixed(1 / all.longest_over_shortest_per_um, 0)} the raw rate showed. Something is there. It is
              about a twentieth of the size the ratio advertises.
            </p>
            <p>
              The mean and the median part company across the deciles, and only the mean moves. The mean
              connection carries {fixed(shortest.mean_synapses, 1)} synapses in the shortest tenth against{" "}
              {fixed(longest.mean_synapses, 1)} in the longest, a factor of{" "}
              {fixed(shortest.mean_synapses / longest.mean_synapses, 1)}; the median carries{" "}
              {count(shortest.median_synapses)} against {count(longest.median_synapses)}. Over the whole graph the
              mean is {fixed(all.mean_synapses, 1)} against a median of {count(all.median_synapses)}. What thins
              out with length is the upper tail. The shortest tenth of the connections holds{" "}
              {percent(shortest.synapses / totals.synapses)} of every synapse in the graph and the longest tenth{" "}
              {percent(longest.synapses / totals.synapses)}, while the typical connection carries about forty
              wherever its partner sits.
            </p>
            <p>
              The same holds between the two groups of connections whose lengths differ most. Neck-crossing
              connections average {micron(neck.mean_length_um)} against {micron(elsewhere.mean_length_um)}{" "}
              elsewhere, and they buy {fixed(neck.synapses_per_um, 3)} synapses per micrometre against{" "}
              {fixed(elsewhere.synapses_per_um, 3)}, a factor of{" "}
              {fixed(elsewhere.synapses_per_um / neck.synapses_per_um, 1)} worse. Per connection, though, they
              carry a median of {count(neck.median_synapses)} synapses against {count(elsewhere.median_synapses)}.
              Inside each group the correlation with length is {fixed(neck.correlation.spearman_rho, 3)} and{" "}
              {fixed(elsewhere.correlation.spearman_rho, 3)}; both are negligible. Between them the two groups
              hold {percent(neck.wire_um / all.wire_um)} and {percent(elsewhere.wire_um / all.wire_um)} of the
              wire against {percent(neck.synapses / all.synapses)} and{" "}
              {percent(elsewhere.synapses / all.synapses)} of the synapses.
            </p>
            <p>
              Each group also has its own ten deciles, and inside them the relation is weaker still. Within the
              neck-crossing connections, whose lengths are the most alike, the longest tenth buys{" "}
              {fixed(neck.longest_over_shortest_per_um, 2)} of what the shortest tenth buys per micrometre — a
              fall of {fixed(1 / neck.longest_over_shortest_per_um, 1)} rather than{" "}
              {fixed(1 / all.longest_over_shortest_per_um, 0)} — and carries a median{" "}
              {fixed(neck.longest_over_shortest_median, 2)} times as large, so the load per connection runs the
              other way. Within everything else the longest tenth buys{" "}
              {fixed(elsewhere.longest_over_shortest_per_um, 3)} of the shortest tenth&rsquo;s rate and carries a
              median {fixed(elsewhere.longest_over_shortest_median, 2)} of its load.
            </p>
            <p>
              This is a null result and it is the finding worth stating. A cell type pays for reach by the
              micrometre and receives, for each connection it makes, a synaptic contact of much the same size
              wherever the partner sits. What the extra wire buys is reach, not weight, and nothing here says that
              a connection which cost more to build carries a heavier load.
            </p>
          </TextBlock>

          <Figure
            number={13}
            title="A long connection carries about as many synapses as a short one"
            caption={
              <>
                The {count(totals.edges)} connections sorted by length into {totals.deciles} equal groups, read
                two ways. Synapses per micrometre: the rate each decile buys at, against the rate it would show
                if synapse count did not depend on length at all; the two run close together, so the{" "}
                {fixed(1 / all.longest_over_shortest_per_um, 0)}-fold fall from the shortest decile to the longest
                is mostly the length in the denominator. Synapses on one connection: what a connection actually
                carries. The median barely moves, from {count(shortest.median_synapses)} to{" "}
                {count(longest.median_synapses)}, while the mean falls from {fixed(shortest.mean_synapses, 1)} to{" "}
                {fixed(longest.mean_synapses, 1)}. Both value axes are logarithmic. Hover or focus a decile for
                its length range, its counts and both readings.
              </>
            }
          >
            <SynapseValue data={data} />
            <More summary="Values behind Figure 13">
              <SynapseTable data={data} />
            </More>
          </Figure>

          <TextBlock
            notes={[
              <Keynote key="factor" value={times(factor, 1)}>
                as much efficiency lost per metre of wire taken from the short end of the length distribution as
                from the long end
              </Keynote>,
              <Sidenote key="arithmetic" title="Arithmetic again">
                The median connection is {micron(graph.median_length_um)} long against a mean of{" "}
                {micron(graph.mean_length_um)}, so the same budget taken from the short end removes{" "}
                {fixed(at["shortest first"].edges_removed / at["longest first"].edges_removed, 1)} times as many
                connections.
              </Sidenote>,
              <Sidenote key="measure" title="Why efficiency, not path length">
                Removal is exactly what makes pairs unreachable, and the mean of a set containing infinities is
                undefined. An unreachable pair contributes a well-defined zero to efficiency, so that is the
                measure used.
              </Sidenote>,
            ]}
          >
            <p>
              The second thing the wire could be buying is connectivity. Connections are removed from the graph
              cumulatively under three schedules — longest first, shortest first, and at random — and what is left
              is measured at {sampling.points} points along the way. Efficiency here is the mean of 1/d over
              ordered pairs of cell types, d the directed shortest path in connections, estimated from one fixed
              sample of {sampling.sources} source nodes drawn once and used at every point of every schedule, so
              the curves differ only in what was removed. The whole graph stands at{" "}
              {fixed(baseline.efficiency, 4)}, and every value below is given as a share of it.
            </p>
            <p>
              Matched on the wire, the short end is far the better buy. Taking{" "}
              {percent(comparison.reference_wire_fraction, 0)} of the budget,{" "}
              {millimetre(at["longest first"].wire_removed_um)}, from the long end costs{" "}
              {count(at["longest first"].edges_removed)} connections, {percent(at["longest first"].edges_removed_share)}{" "}
              of them, and leaves efficiency at {percent(at["longest first"].efficiency_share)}. The same wire from
              the short end costs {count(at["shortest first"].edges_removed)} connections,{" "}
              {percent(at["shortest first"].edges_removed_share)}, and leaves it at{" "}
              {percent(at["shortest first"].efficiency_share)}. Per metre removed that is{" "}
              {percent(perMetre["longest first"], 2)} of the starting efficiency lost from the long end against{" "}
              {percent(perMetre["shortest first"], 2)} from the short end.
            </p>
            <p>
              Matched on the number of connections instead, the comparison reverses, and the second view of the
              figure shows it. Removing the {count(at["longest first"].edges_removed)} longest leaves{" "}
              {percent(at["longest first"].efficiency_share)}; removing the same number at random leaves{" "}
              {percent(at["random, matched count"].efficiency_share)} ±{" "}
              {percent(at["random, matched count"].efficiency_share_sd)} over {sampling.random_repeats} draws. The
              longest connections are individually worth more to the graph than typical ones. They are simply not
              worth their length: the budget spent on the long tail is not the cheapest way to keep the graph
              short-pathed, whatever else it is for.
            </p>
          </TextBlock>

          <Figure
            number={14}
            title="Per micrometre, short connections buy more connectivity; per connection, long ones are worth more"
            caption={
              <>
                Efficiency of the cell-type graph, as a share of the {fixed(baseline.efficiency, 4)} the whole
                graph reaches, against how much has been removed. Read by the wire, the longest-first and
                shortest-first schedules are matched by construction and the gap between them at{" "}
                {percent(comparison.reference_wire_fraction, 0)} is the factor of {fixed(factor, 1)} per metre.
                Read by the number of connections, the longest-first and random schedules are matched instead, and
                the longest connections turn out to cost more than typical ones. The random schedule is the mean of{" "}
                {sampling.random_repeats} draws. Hover or focus a sample point for all three schedules at once.
              </>
            }
            controls={
              <Segmented label="Match the schedules on" options={AXES} value={axis} onChange={setAxis} />
            }
          >
            <Efficiency data={data} axis={axis} />
            <p className="visually-hidden" aria-live="polite">
              Schedules matched on the {axisLabel(axis)}.
            </p>
            <More summary="Values behind Figure 14">
              <EfficiencyTable data={data} />
            </More>
          </Figure>

          <TextBlock>
            <p>
              The other measure taken at every point says nothing at all, and it is reported here at the same size
              as the one that does. None of the three schedules breaks the graph apart over the range sampled. The
              largest weakly connected component holds {count(baseline.largest_component)} of the{" "}
              {count(graph.nodes)} cell types to begin with and still holds{" "}
              {percent(at["longest first"].largest_component_share)} of them after a quarter of the wire is taken
              from the long end, {percent(at["shortest first"].largest_component_share)} after the same wire is
              taken from the short end, and {percent(at["random, matched count"].largest_component_share)} after
              the matched number of random removals.
            </p>
            <p>
              At the far end of the sampled range the two measures have come apart completely. With{" "}
              {percent(far.long.wire_removed_share, 0)} of the wire gone the long-end schedule has cost{" "}
              {percent(1 - far.long.efficiency_share)} of the efficiency while leaving{" "}
              {percent(far.long.largest_component_share)} of the nodes in one component, and the short-end
              schedule has cost {percent(1 - far.short.efficiency_share)} of it while still leaving{" "}
              {percent(far.short.largest_component_share)} of them in one. Component size is a blunt instrument at
              this density. That is a null for the component measure rather than evidence that the graph is robust
              in any useful sense, and reading it as robustness would be the mistake this figure exists to
              prevent.
            </p>
          </TextBlock>

          <Figure
            number={15}
            title="Efficiency collapses while the graph is still almost entirely one piece"
            caption={
              <>
                Share of the {count(graph.nodes)} cell types left in the largest weakly connected component under
                the same three schedules, against the wire removed. The value axis starts at three quarters, not
                at zero, because nothing here comes near the bottom of it. Only the short-end schedule moves at
                all, and only once most of the budget is gone. Hover or focus a sample point for all three
                schedules at once.
              </>
            }
          >
            <Component data={data} />
            <More summary="Values behind Figure 15">
              <ComponentTable data={data} />
            </More>
          </Figure>
        </HeadingLevel>
      </div>
    </section>
  );
}
