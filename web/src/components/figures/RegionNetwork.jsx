import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, barPath } from "../Chart.jsx";
import { useRovingRows } from "./useRovingRows.js";
import { TableWrap } from "../ui.jsx";
import { count, fixed, millimetre, percent, pValue, times } from "../../lib/format.js";
import { useMedia } from "../../lib/hooks.js";
import { log } from "../../lib/scales.js";

/** The two nulls, both of which preserve every region's number of partners exactly. */
export const NULLS = [
  { value: "rewired", label: "Rewired" },
  { value: "weights shuffled", label: "Weights shuffled" },
];

export const METRICS = [
  ["clustering", "Clustering", 3],
  ["path_length", "Path length", 3],
  ["weighted_clustering", "Clustering by wire", 3],
  ["weighted_path_length", "Path length by wire", 1],
];

const DOMAIN = [0.75, 16];
const TICKS = [1, 2, 5, 10];
const ROW = 34;
const STACKED_ROW = 52;

const nullName = (key) => NULLS.find((option) => option.value === key).label.toLowerCase();

export default function RegionNetwork({ data, model }) {
  const [hover, setHover] = useState(null);
  const wide = useMedia("(min-width: 700px)");
  const nulls = data.regions.small_world.nulls[model];
  const rows = METRICS.map(([key, label, digits]) => ({ key, label, digits, result: nulls[key] }));
  const margin = { top: 30, right: 56, bottom: 46, left: wide ? 168 : 12 };
  const height = margin.top + margin.bottom + rows.length * (wide ? ROW : STACKED_ROW);
  const rowProps = useRovingRows(
    rows.map((row) => row.key),
    (key) => setHover(key == null ? null : rows.findIndex((row) => row.key === key)),
  );
  const clamp = (value) => Math.min(Math.max(value, DOMAIN[0]), DOMAIN[1]);

  return (
    <ChartFrame
      height={height}
      margin={margin}
      role="group"
      label={`Four measures of the region network as a multiple of the mean of ${count(
        data.regions.totals.n_nulls,
      )} ${nullName(model)} nulls, with each null's central 95% range.`}
      onPointer={(_x, y, inner) => {
        const index = Math.floor(y / (inner.height / rows.length));
        setHover(index >= 0 && index < rows.length ? index : null);
      }}
      onLeave={() => setHover(null)}
      overlay={({ height: inner, margin: m, width }) => {
        if (hover == null) return null;
        const row = rows[hover];
        const step = inner / rows.length;
        const x = log(DOMAIN, [0, width - m.left - m.right]);
        return (
          <Tooltip x={m.left + x(clamp(row.result.ratio))} y={m.top + hover * step + step / 2 - 4} width={width}>
            <div className="tip-title">{row.label}</div>
            <Row label="Real" value={fixed(row.result.real, row.digits)} />
            <Row label="Null mean" value={fixed(row.result.null_mean, row.digits)} />
            <Row
              label="Null central 95%"
              value={`${fixed(row.result.null_lo, row.digits)} to ${fixed(row.result.null_hi, row.digits)}`}
            />
            <Row label="Real / null" value={times(row.result.ratio, 3)} />
            <Row label="p" value={pValue(row.result.p_value)} />
          </Tooltip>
        );
      }}
    >
      {({ width, height: inner }) => {
        const x = log(DOMAIN, [0, width]);
        const step = inner / rows.length;
        return (
          <g>
            <XAxis
              scale={x}
              ticks={TICKS}
              height={inner}
              width={width}
              margin={margin}
              format={(t) => `${t}×`}
              title="Real value / null mean"
            />
            {/* Where the real network matches its null. Narrow, the names run above the marks, so the rule is
                cut into one segment per row and passes behind them rather than through them. */}
            {wide ? (
              <line x1={x(1)} x2={x(1)} y1={-6} y2={inner} stroke="var(--rule-strong)" strokeDasharray="3 3" />
            ) : (
              rows.map((row, i) => (
                <line
                  key={row.key}
                  x1={x(1)}
                  x2={x(1)}
                  y1={i * step + 18}
                  y2={(i + 1) * step}
                  stroke="var(--rule-strong)"
                  strokeDasharray="3 3"
                />
              ))
            )}
            {rows.map((row, i) => {
              const top = i * step;
              const y = wide ? top + step / 2 : top + step / 2 + 9;
              const lo = x(clamp(row.result.null_lo / row.result.null_mean));
              const hi = x(clamp(row.result.null_hi / row.result.null_mean));
              const inside = row.result.ratio >= row.result.null_lo / row.result.null_mean &&
                row.result.ratio <= row.result.null_hi / row.result.null_mean;
              return (
                <g
                  key={row.key}
                  {...rowProps(row.key)}
                  role="img"
                  aria-label={`${row.label}: ${fixed(row.result.ratio, 3)} times the ${nullName(
                    model,
                  )} null mean, real ${fixed(row.result.real, row.digits)} against ${fixed(
                    row.result.null_mean,
                    row.digits,
                  )}, p ${pValue(row.result.p_value)}`}
                >
                  <rect
                    className="row-band"
                    x={-margin.left + 2}
                    width={width + margin.left + margin.right - 4}
                    y={top + 1}
                    height={step - 2}
                    rx={3}
                  />
                  {wide ? (
                    <text className="row-label" x={-12} y={y} dy="0.32em" textAnchor="end">
                      {row.label}
                    </text>
                  ) : (
                    <text className="row-label" x={0} y={top + 12}>
                      {row.label}
                    </text>
                  )}
                  <path data-mark="bar" d={barPath(lo, y - 4.5, Math.max(3, hi - lo), 9, 2)} fill="var(--wash)" />
                  <circle
                    data-mark="fade"
                    cx={x(clamp(row.result.ratio))}
                    cy={y}
                    r="5"
                    fill={inside ? "var(--paper)" : "var(--wire)"}
                    stroke={inside ? "var(--ink-2)" : "var(--wire)"}
                    strokeWidth="2"
                  />
                  <text className="mark-label" x={width + 8} y={y} dy="0.32em">
                    {fixed(row.result.ratio, row.result.ratio >= 10 ? 1 : 2)}
                  </text>
                </g>
              );
            })}
          </g>
        );
      }}
    </ChartFrame>
  );
}

const SPLITS = [
  ["compartment", "brain or nerve cord"],
  ["side", "left or right"],
  ["segment", "thoracic segment"],
];

/** The values behind the figure: both nulls, the largest regions, the two communities and the anatomy. */
export function RegionTable({ data }) {
  const { small_world: world, totals, top_regions: top, communities, anatomy, partition, mirrored } = data.regions;
  const shown = top.reduce((sum, row) => sum + row.strength_share, 0);
  return (
    <>
      <TableWrap label="Values behind Figure 18: the four measures against both nulls">
        <table className="data">
          <caption>
            Clustering is the mean local clustering coefficient and path length the mean shortest path over all
            pairs; the weighted versions weigh a pair by its wire, a step along the heaviest pair of regions
            costing one and a thinner pair proportionally more. {count(totals.n_nulls)} draws of each null, both
            preserving every region&rsquo;s number of partners exactly. The weight-shuffled null leaves the real
            topology alone, so it reproduces the two unweighted measures by construction.
          </caption>
          <thead>
            <tr>
              <th scope="col">Measure</th>
              <th scope="col" className="num-col">
                Real
              </th>
              {NULLS.map((option) => (
                <th scope="col" className="num-col" key={option.value}>
                  {option.label} null
                </th>
              ))}
              {NULLS.map((option) => (
                <th scope="col" className="num-col" key={`${option.value}-ratio`}>
                  Real / {option.label.toLowerCase()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS.map(([key, label, digits]) => (
              <tr key={key}>
                <th scope="row">{label}</th>
                <td className="num-col">{fixed(world.real[key], digits)}</td>
                {NULLS.map((option) => (
                  <td className="num-col" key={option.value}>
                    {fixed(world.nulls[option.value][key].null_mean, digits)} ±{" "}
                    {fixed(world.nulls[option.value][key].null_sd, digits + 1)}
                  </td>
                ))}
                {NULLS.map((option) => (
                  <td className="num-col" key={`${option.value}-ratio`}>
                    {fixed(world.nulls[option.value][key].ratio, 3)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>

      <TableWrap label="Values behind Figure 18: the regions holding the most wire">
        <table className="data">
          <caption>
            The {count(top.length)} regions holding the most wire, of {count(totals.regions)}. Strength is the wire
            running between a region and every other; a micrometre between two regions belongs to both, so the
            strengths sum to twice the between-region wire. These {count(top.length)} hold {percent(shown)} of it.
          </caption>
          <thead>
            <tr>
              <th scope="col">Region</th>
              <th scope="col">Compartment</th>
              <th scope="col" className="num-col">
                Community
              </th>
              <th scope="col" className="num-col">
                Cell types
              </th>
              <th scope="col" className="num-col">
                Partners
              </th>
              <th scope="col" className="num-col">
                Strength
              </th>
              <th scope="col" className="num-col">
                Share
              </th>
              <th scope="col" className="num-col">
                Wire staying inside
              </th>
            </tr>
          </thead>
          <tbody>
            {top.map((row) => (
              <tr key={row.neuropil}>
                <th scope="row">{row.neuropil}</th>
                <td>{row.compartment === "vnc" ? "nerve cord" : "brain"}</td>
                <td className="num-col">{row.community}</td>
                <td className="num-col">{count(row.types)}</td>
                <td className="num-col">{count(row.degree)}</td>
                <td className="num-col">{millimetre(row.strength_um)}</td>
                <td className="num-col">{percent(row.strength_share)}</td>
                <td className="num-col">{millimetre(row.internal_um)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>

      <TableWrap label="Values behind Figure 18: the two communities and the anatomy they follow">
        <table className="data">
          <caption>
            Louvain on the wire-weighted region graph returns {partition.communities} communities with a modularity
            of {fixed(partition.modularity, 3)}; all {count(partition.seeds)} random seeds return the same
            partition.
          </caption>
          <thead>
            <tr>
              <th scope="col">Community</th>
              <th scope="col" className="num-col">
                Regions
              </th>
              <th scope="col" className="num-col">
                Brain
              </th>
              <th scope="col" className="num-col">
                Nerve cord
              </th>
              <th scope="col" className="num-col">
                Strength
              </th>
            </tr>
          </thead>
          <tbody>
            {communities.map((row) => (
              <tr key={row.community}>
                <th scope="row">{row.community}</th>
                <td className="num-col">{count(row.regions)}</td>
                <td className="num-col">{count(row.brain_regions)}</td>
                <td className="num-col">{count(row.vnc_regions)}</td>
                <td className="num-col">{millimetre(row.strength_um)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>

      <TableWrap label="Values behind Figure 18: the partition against three anatomical splits">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Anatomical split</th>
              <th scope="col" className="num-col">
                Regions labelled
              </th>
              <th scope="col" className="num-col">
                Groups
              </th>
              <th scope="col" className="num-col">
                Adjusted Rand
              </th>
              <th scope="col" className="num-col">
                Normalized mutual information
              </th>
            </tr>
          </thead>
          <tbody>
            {SPLITS.map(([key, label]) => (
              <tr key={key}>
                <th scope="row">{label}</th>
                <td className="num-col">{count(anatomy[key].regions)}</td>
                <td className="num-col">{count(anatomy[key].groups)}</td>
                <td className="num-col">{fixed(anatomy[key].adjusted_rand, 3)}</td>
                <td className="num-col">{fixed(anatomy[key].nmi, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      <p className="caption">
        Of the {count(mirrored.neuropils_on_both_sides)} neuropils present on both sides, only{" "}
        {mirrored.split.join(", ")} has its two copies in different communities, and the leg neuropils of all three
        thoracic segments sit together. The recomputed matrix reproduces the wire atlas total of{" "}
        {millimetre(data.regions.atlas_agreement.atlas_total_wire_um)} and every one of the{" "}
        {count(data.regions.atlas_agreement.pairs_reproduced)} pairs the atlas saves.
      </p>
    </>
  );
}
