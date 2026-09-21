import { useState } from "react";
import HubPlacement, { HubPlacementTable } from "./figures/HubPlacement.jsx";
import RegionNetwork, { NULLS, RegionTable } from "./figures/RegionNetwork.jsx";
import WireSymmetry, { SymmetryTable, VIEWS, pairsFor } from "./figures/WireSymmetry.jsx";
import { Figure, HeadingLevel, Keynote, More, Segmented, Sidenote, TextBlock, Unregistered } from "./ui.jsx";
import { count, fixed, list, micron, percent, pValue, signed, times } from "../lib/format.js";

const metres = (um) => `${fixed(um / 1e6, 2)} m`;

const viewLabel = (value) => VIEWS.find((option) => option.value === value).label.toLowerCase();
const nullLabel = (value) => NULLS.find((option) => option.value === value).label.toLowerCase();

export default function Anatomy({ data }) {
  const [view, setView] = useState("wire");
  const [model, setModel] = useState("rewired");

  const hubs = data.hubs;
  const byScope = Object.fromEntries(
    hubs.correlations.filter((row) => row.measure === "degree").map((row) => [row.scope, row]),
  );
  const partners = hubs.partners.scopes;
  const strongest = hubs.correlations.reduce((worst, row) =>
    Math.abs(row.spearman_rho) > Math.abs(worst.spearman_rho) ? row : worst,
  );

  const symmetry = data.symmetry;
  const wire = symmetry.wire_asymmetry;
  const cost = symmetry.cost_ratio_asymmetry;
  const widest = symmetry.pairs.reduce((worst, pair) =>
    Math.abs(pair.log_ratio) > Math.abs(worst.log_ratio) ? pair : worst,
  );
  const largestMidline = symmetry.midline.slice(0, 4);
  const shown = pairsFor(data, view);
  // Pairs in order of the wire they hold, so a gap can be read against what is at stake in it.
  const bySize = [...symmetry.pairs].sort(
    (a, b) => b.wire_left_um + b.wire_right_um - (a.wire_left_um + a.wire_right_um),
  );
  const pairWire = (pair) => pair.wire_left_um + pair.wire_right_um;
  const tightest = Math.exp(Math.max(...bySize.slice(0, 10).map((pair) => Math.abs(pair.log_ratio))));
  const lopsided = bySize.filter((pair) => Math.abs(pair.log_ratio) > Math.LN2);
  const smallestRank = bySize.length - bySize.indexOf(lopsided[0]);
  const lopsidedShare =
    lopsided.reduce((sum, pair) => sum + pairWire(pair), 0) / bySize.reduce((sum, pair) => sum + pairWire(pair), 0);
  const leanLeft = symmetry.pairs.filter((pair) => pair.log_ratio > 0).length;
  const brainPairs = symmetry.pairs.filter((pair) => pair.compartment === "brain").length;
  const typeGaps = symmetry.pairs
    .map((pair) => Math.abs(pair.types_left - pair.types_right) / Math.max(pair.types_left, pair.types_right))
    .sort((a, b) => a - b);
  const medianTypeGap = (typeGaps[(typeGaps.length - 1) >> 1] + typeGaps[typeGaps.length >> 1]) / 2;
  const widestTypes = symmetry.pairs.reduce((worst, pair) =>
    Math.abs(pair.types_left - pair.types_right) > Math.abs(worst.types_left - worst.types_right) ? pair : worst,
  );

  const regions = data.regions;
  const totals = regions.totals;
  const rewired = regions.small_world.nulls.rewired;
  const top = regions.top_regions;
  const hub = top[0];
  const topShare = top.reduce((sum, row) => sum + row.strength_share, 0);

  return (
    <section className="section" id="anatomy" aria-labelledby="anatomy-title">
      <div className="wrap">
        <HeadingLevel level={3}>
          <div className="section-head">
            <h2 id="anatomy-title">The same wire, read against the anatomy</h2>
            <p className="lede">
              Three more questions the budget can be asked once it is laid over the body: where the best connected
              cell types sit, whether the two sides of the animal cost the same, and what the regions look like as
              a network in their own right.
            </p>
          </div>

          <Unregistered>
            These three analyses, like the two above, were run after the thirteen registered hypotheses had been
            tested. None carries a registered hypothesis, none had a direction fixed in advance, and their
            p-values are uncorrected. They are description, not tests. The communities below are groupings of
            anatomy by wire, not functional modules, and the efficiency above is a graph measure over shortest
            paths, not a statement about signalling.
          </Unregistered>

          <TextBlock
            notes={[
              <Keynote key="ratio" value={fixed(partners.all.ratio, 3)}>
                the distance from a cell type to the centroid of its own partners, over the distance to
                degree-matched random ones
              </Keynote>,
              <Sidenote key="signs" title="The two halves disagree">
                Degree against distance from the centre runs {signed(byScope.brain.spearman_rho, 3)} in the brain
                and {signed(byScope["nerve cord"].spearman_rho, 3)} in the nerve cord. Pooling them would cancel
                two weak tendencies into one number belonging to neither.
              </Sidenote>,
              <Sidenote key="centre" title="Which centre">
                Distance is measured from the centroid of the cell types of that scope, not of the whole specimen.
                A shared centre would rank a type by which compartment it belongs to rather than by where it sits
                inside it.
              </Sidenote>,
            ]}
          >
            <p>
              A cell type that is heavily connected pays its position on every one of its connections, so wiring
              economy predicts that the best connected types sit centrally. Over all{" "}
              {count(hubs.totals.types)} cell types the rank correlation between total degree and distance from
              the centre of the compartment is {signed(byScope.all.spearman_rho, 3)}. That is no relationship at
              all, and the largest correlation anywhere in the table, {signed(strongest.spearman_rho, 3)} for{" "}
              {strongest.measure} in the {strongest.scope} scope, is still small enough to leave the prediction
              unsupported. The left panel of the figure shows why: the median distance from the centre is nearly
              flat across ten degree deciles in every scope.
            </p>
            <p>
              The second test on the same cell types is not a null. Each type is compared with{" "}
              {count(partners.all.permutations)} redraws in which it keeps its degree and takes that many partners
              uniformly at random from the other types, never itself, with replacement. The mean distance from a
              type to the centroid of its real partners is {micron(partners.all.real_um, 1)} against{" "}
              {micron(partners.all.null_mean_um, 1)} for random partners, a ratio of {fixed(partners.all.ratio, 3)}{" "}
              at z = {fixed(partners.all.z_score, 1)}, with {count(partners.all.n_at_or_below_real)} of{" "}
              {count(partners.all.permutations)} redraws as near. {percent(hubs.partners.share_nearer_than_chance)}{" "}
              of the {count(hubs.partners.types_tested)} tested types lie nearer their own partners than their own
              null mean. The effect holds in both compartments, at {fixed(partners.brain.ratio, 3)} in the brain
              and {fixed(partners["nerve cord"].ratio, 3)} in the nerve cord.
            </p>
            <p>
              Taken together the two say that placement economy here is local rather than radial. A type is placed
              among the cells it actually contacts, but how well connected it is says next to nothing about how
              far from the middle of its compartment it sits. Neither result was predicted in advance, and the
              first is a null against a prediction the wiring-economy literature would have made.
            </p>
          </TextBlock>

          <Figure
            number={16}
            title="Degree does not say how centrally a cell type sits, but a type sits close to the cells it contacts"
            caption={
              <>
                Two panels over the same {count(hubs.totals.types)} cell types, for all of them and for the brain
                and the nerve cord apart. Distance from the centre: the median distance to the centroid of the
                scope against ten degree deciles. The lines are close to flat, and the value axis runs from zero
                so that flatness can be read directly. Distance to the partners: the mean distance from a cell
                type to the centroid of its own partners against the same types&rsquo; degree-matched random
                partners, over {count(partners.all.permutations)} redraws. Hover or focus a decile, or a scope,
                for the values behind each mark.
              </>
            }
          >
            <HubPlacement data={data} />
            <More summary="Values behind Figure 16">
              <HubPlacementTable data={data} />
            </More>
          </Figure>

          <TextBlock
            notes={[
              <Keynote key="median" value={times(Math.exp(wire.median_absolute), 2)}>
                the factor separating the two sides of the median left&ndash;right pair of neuropils
              </Keynote>,
              <Sidenote key="null" title="No side bias">
                The mean log ratio is {signed(wire.mean, 3)} against a sign-flip null spread of{" "}
                {fixed(wire.null_sd, 4)}: z = {fixed(wire.z_score, 2)}, two-sided p = {pValue(wire.p_value)} over{" "}
                {count(wire.permutations)} flips.
              </Sidenote>,
              <Sidenote key="weak" title="A weak null is still a null">
                Matching each left neuropil to a random right one gives a mean absolute log ratio of{" "}
                {fixed(wire.repaired_null_mean, 3)} against {fixed(wire.mean_absolute, 3)} observed. Counterparts
                are far more alike than arbitrary neuropils, which is what the naming asserts; it sets no scale for
                how alike two copies of one structure ought to be.
              </Sidenote>,
            ]}
          >
            <p>
              Of the {count(symmetry.totals.neuropils)} neuropils that hold cell types,{" "}
              {count(symmetry.totals.paired.neuropils)} form {count(wire.pairs)} left&ndash;right pairs and carry{" "}
              {percent(symmetry.totals.paired.wire_share)} of the {metres(symmetry.totals.total_wire_um)} of wire.
              Within a pair the two sides hold wire within a factor of{" "}
              {fixed(Math.exp(wire.median_absolute), 2)} of each other at the median and{" "}
              {fixed(Math.exp(wire.mean_absolute), 2)} on average. The widest gap is {widest.neuropil}, where the
              larger copy holds {fixed(Math.exp(Math.abs(widest.log_ratio)), 1)} times the wire of the other over{" "}
              {count(Math.max(widest.types_left, widest.types_right))} cell types against{" "}
              {count(Math.min(widest.types_left, widest.types_right))}.
            </p>
            <p>
              The gap does not widen with the amount of wire at stake; it narrows. The{" "}
              {count(10)} pairs holding the most wire all sit within a factor of {fixed(tightest, 2)} of balance.
              Only {count(lopsided.length)} of the {count(wire.pairs)} pairs part by more than a factor of two —{" "}
              {list(lopsided.map((pair) => pair.neuropil))} — and all of them are among the{" "}
              {count(smallestRank)} smallest pairs by wire, holding {percent(lopsidedShare, 2)} of the paired
              budget between them. The widest gaps sit where a single cell type either way moves the number.
            </p>
            <p>
              Two nulls, because the question has two halves. If the two hemispheres are wired alike then the sign
              of a pair&rsquo;s log ratio is arbitrary, so negating each pair&rsquo;s ratio at random gives the
              null distribution of their mean; the observed mean of {signed(wire.mean, 3)} sits inside it at z ={" "}
              {fixed(wire.z_score, 2)}, two-sided p = {pValue(wire.p_value)}. Matching each left neuropil to a
              right neuropil drawn at random rather than to its own counterpart gives the asymmetry expected
              between two unrelated structures, {fixed(wire.repaired_null_mean, 3)} ±{" "}
              {fixed(wire.repaired_null_sd, 3)}, against {fixed(wire.mean_absolute, 3)} observed. On neither test
              is the observed asymmetry larger than expected.
            </p>
            <p>
              Nor is there a direction to find. {count(leanLeft)} of the {count(wire.pairs)} pairs hold more wire
              on the left and {count(wire.pairs - leanLeft)} on the right, which is the arbitrariness the
              sign-flip null is built on, and across all of them the right side holds a geometric mean of{" "}
              {fixed(Math.exp(-wire.mean), 3)} times the wire of the left. The pairing is by name rather than by
              content, and the two sides need not hold the same cell types: over the{" "}
              {count(wire.pairs)} pairs their numbers differ by a median of {percent(medianTypeGap, 0)}, reaching{" "}
              {widestTypes.neuropil}, which holds {count(widestTypes.types_left)} types on the left against{" "}
              {count(widestTypes.types_right)} on the right. Some of the wire gap is that rather than a
              difference in how much wire the same cells lay down.
            </p>
            <p>
              The same holds for how economically each copy is wired inside itself. {count(cost.pairs)} pairs have
              an internal cost ratio on both sides; the mean left-minus-right difference is {signed(cost.mean, 4)}{" "}
              against a sign-flip null spread of {fixed(cost.null_sd, 4)} (z = {fixed(cost.z_score, 2)}, p ={" "}
              {pValue(cost.p_value)}), and the mean absolute difference is {fixed(cost.mean_absolute, 4)} on ratios
              that all sit below one. Whatever placement economy a neuropil has, its opposite copy has about the
              same amount of it. The second view of the figure draws those {count(cost.pairs)} differences.
            </p>
            <p>
              The left&ndash;right difference in this specimen&rsquo;s wiring budget is a null result, and it is
              given the space here that a positive one would get. The {count(symmetry.totals.midline.neuropils)}{" "}
              neuropils carrying no hemisphere suffix are not in either test and hold{" "}
              {percent(symmetry.totals.midline.wire_share)} of the wire between them. Four of them —{" "}
              {list(largestMidline.map((row) => row.neuropil))} — hold{" "}
              {percent(largestMidline.reduce((sum, row) => sum + row.wire_share, 0))} of the specimen&rsquo;s wire
              between them, the largest single holder in the specimen being {largestMidline[0].neuropil} at{" "}
              {metres(largestMidline[0].wire_um)}, so most of the budget that falls outside the
              left&ndash;right question falls in four places rather than in a long tail. The{" "}
              {count(symmetry.totals.unpaired_sides.neuropils)} that are one side of a structure whose other side
              holds no cell type here are listed in the values below rather than dropped.
            </p>
          </TextBlock>

          <Figure
            number={17}
            title="The two hemispheres hold the same wire, and neither holds systematically more"
            caption={
              <>
                Each mark is one left&ndash;right pair of neuropils, largest by wire first, drawn at the
                difference between its two sides against a line where the two are in balance. The{" "}
                {count(brainPairs)} brain pairs are in copper and the {count(wire.pairs - brainPairs)} nerve-cord
                pairs in grey, and the dashed rule is the mean over all of them. Read by the
                wire held, the {count(wire.pairs)} pairs scatter either side of balance with no systematic lean;
                read by internal economy, the {count(cost.pairs)} pairs that have a cost ratio on both sides do
                the same. Hover or focus a pair for both of its sides.
              </>
            }
            controls={<Segmented label="Compare the two sides on" options={VIEWS} value={view} onChange={setView} />}
          >
            <WireSymmetry data={data} view={view} />
            <p className="visually-hidden" aria-live="polite">
              Comparing the two sides on {viewLabel(view)}, over {shown.length} pairs.
            </p>
            <More summary="Values behind Figure 17">
              <SymmetryTable data={data} view={view} />
            </More>
          </Figure>

          <TextBlock
            notes={[
              <Keynote key="paths" value={times(rewired.weighted_path_length.ratio, 1)}>
                the length of the network&rsquo;s wire-weighted shortest paths against a degree-preserving
                rewiring &mdash; longer, not shorter
              </Keynote>,
              <Sidenote key="density" title="Too dense to answer unweighted">
                At {percent(totals.density)} density almost every pair of regions is already joined, so the
                unweighted clustering is {fixed(regions.small_world.real.clustering, 3)} against a null mean of{" "}
                {fixed(rewired.clustering.null_mean, 3)} and the mean path is{" "}
                {fixed(regions.small_world.real.path_length, 2)} steps against{" "}
                {fixed(rewired.path_length.null_mean, 2)}.
              </Sidenote>,
              <Sidenote key="second" title="The second null agrees">
                Leaving the real topology alone and permuting only the wire over it reproduces the same direction
                at {times(regions.small_world.nulls["weights shuffled"].weighted_path_length.ratio, 1)} the null
                mean, so the long paths come from the arrangement of the wire rather than from which pairs are
                joined.
              </Sidenote>,
            ]}
          >
            <p>
              Collapsing the cell-type graph onto the neuropils gives a network of {count(totals.regions)} regions
              joined by {count(totals.region_edges)} weighted edges, {percent(totals.density)} of the{" "}
              {count(totals.possible_region_edges)} pairs that could be joined. Every cell type takes the nearest
              published neuropil surface and each connection lends half its length to the region at each of its
              ends, the rule the wire atlas uses; the recomputed matrix reproduces the atlas total of{" "}
              {metres(regions.atlas_agreement.atlas_total_wire_um)} and every one of the{" "}
              {count(regions.atlas_agreement.pairs_reproduced)} pairs the atlas saves.{" "}
              {percent(totals.share_between_regions)} of the wire runs between two regions and the rest stays
              inside one.
            </p>
            <p>
              {hub.neuropil} is the largest hub by wire, holding {metres(hub.strength_um)} to{" "}
              {count(hub.degree)} of the other {count(totals.regions - 1)} regions,{" "}
              {percent(hub.strength_share)} of all between-region wire, and the {count(top.length)} largest regions
              hold {percent(topShare)} of it between them. Degree separates the regions far less than wire does:
              the median region has {count(totals.median_degree)} partners and the least connected has{" "}
              {count(totals.min_degree)}.
            </p>
            <p>
              The network is not small-world by wire. Against {count(totals.n_nulls)} degree-preserving rewirings
              it is {fixed(rewired.weighted_clustering.ratio, 3)} times as clustered by wire, but its weighted
              paths are {fixed(rewired.weighted_path_length.ratio, 1)} times <i>longer</i>, not shorter, which puts
              the wire-weighted small-world ratio at {fixed(rewired.weighted_sigma, 3)} — far below the one a
              small-world network would give. Long weighted paths are the expected consequence of heavy pairs of
              regions sitting together rather than bridging the network, and the second null, which keeps the
              topology and moves only the wire, reproduces the same direction.
            </p>
            <p>
              Louvain on the wire-weighted graph returns exactly {regions.partition.communities} communities with a
              modularity of {fixed(regions.partition.modularity, 3)}, and all {count(regions.partition.seeds)}{" "}
              random seeds return the same partition. They follow the brain and nerve cord split and nothing else:
              an adjusted Rand index of {fixed(regions.anatomy.compartment.adjusted_rand, 3)} against compartment
              over all {count(regions.anatomy.compartment.regions)} regions,{" "}
              {fixed(regions.anatomy.side.adjusted_rand, 3)} against hemisphere over the{" "}
              {count(regions.anatomy.side.regions)} regions carrying a side, and{" "}
              {fixed(regions.anatomy.segment.adjusted_rand, 3)} against thoracic segment over the{" "}
              {count(regions.anatomy.segment.regions)} that name one. Of the{" "}
              {count(regions.mirrored.neuropils_on_both_sides)} neuropils present on both sides, only{" "}
              {list(regions.mirrored.split)} has its two copies in different communities.
            </p>
            <p>
              The correspondence with the compartment is strong but not exact. The community holding the nerve
              cord holds {regions.brain_with_cord.length} brain neuropils with it —{" "}
              {list(regions.brain_with_cord)} — which are the gnathal and ventral-posterior regions lying
              against the neck. On wire alone they group with the nerve cord rather than with the rest of the
              brain. These are groupings of anatomy by wire and nothing more.
            </p>
          </TextBlock>

          <Figure
            number={18}
            title="Dense and clustered, but its weighted paths run ten times longer than chance"
            caption={
              <>
                Four measures of the {count(totals.regions)}-region network as a multiple of the mean of{" "}
                {count(totals.n_nulls)} nulls, on a logarithmic axis. The pale band is the null&rsquo;s central
                95%: a hollow point inside it is a measure the null reproduces, a filled point outside it is one
                it does not. The rewired null randomizes which pairs of regions are joined and deals the wire over
                the result; the weight-shuffled null keeps the real topology and permutes only the wire, so it
                reproduces both unweighted measures by construction. Hover or focus a row for the values in their
                own units.
              </>
            }
            controls={<Segmented label="Null model" options={NULLS} value={model} onChange={setModel} />}
          >
            <RegionNetwork data={data} model={model} />
            <p className="visually-hidden" aria-live="polite">
              Measured against the {nullLabel(model)} null.
            </p>
            <More summary="Values behind Figure 18">
              <RegionTable data={data} />
            </More>
          </Figure>
        </HeadingLevel>
      </div>
    </section>
  );
}
