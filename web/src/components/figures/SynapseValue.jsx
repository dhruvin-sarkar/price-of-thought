import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, YAxis } from "../Chart.jsx";
import { useRovingRows } from "./useRovingRows.js";
import { TableWrap } from "../ui.jsx";
import { count, fixed, micron, millimetre } from "../../lib/format.js";
import { useMedia } from "../../lib/hooks.js";
import { line, linear, log } from "../../lib/scales.js";

const HEIGHT = 300;

/** The two readings taken over the same ten length deciles: the rate per micrometre, and the load per connection. */
const PANELS = [
  {
    id: "rate",
    domain: [0.08, 20],
    ticks: [0.1, 0.3, 1, 3, 10],
    format: (t) => (t < 1 ? t.toFixed(1) : String(t)),
    title: "Synapses per µm",
    digits: 2,
    series: [
      { key: "synapses_per_um", label: "Observed", color: "var(--wire)", dashed: false },
      { key: "expected_per_um", label: "If length did not matter", color: "var(--ink-3)", dashed: true },
    ],
  },
  {
    id: "load",
    domain: [25, 500],
    ticks: [25, 50, 100, 200, 400],
    format: String,
    title: "Synapses on one connection",
    digits: 1,
    series: [
      { key: "mean_synapses", label: "Mean", color: "var(--null)", dashed: false },
      { key: "median_synapses", label: "Median", color: "var(--ink)", dashed: false },
    ],
  },
];

export const GROUPS = [
  ["all", "All connections"],
  ["across the neck", "Across the neck"],
  ["elsewhere", "Everywhere else"],
];

const clamp = (value, lo, hi) => Math.min(hi, Math.max(lo, value));

export default function SynapseValue({ data }) {
  const deciles = data.synapses.deciles;
  return (
    <div className="panels is-two">
      {PANELS.map((panel) => (
        <DecilePanel key={panel.id} deciles={deciles} panel={panel} />
      ))}
    </div>
  );
}

/** One panel: two series read against the ten length deciles, on a logarithmic value axis. */
function DecilePanel({ deciles, panel }) {
  const [hover, setHover] = useState(null);
  const wide = useMedia("(min-width: 700px)");
  const margin = { top: 34, right: 16, bottom: 48, left: 48 };
  const last = deciles.length;
  const rowProps = useRovingRows(
    deciles.map((row) => row.decile),
    setHover,
  );
  const row = deciles.find((item) => item.decile === hover);
  const reading = (item) =>
    panel.series
      .map((series) => `${series.label.toLowerCase()} ${fixed(item[series.key], panel.digits)}`)
      .join(", ");

  return (
    <div>
      <p className="legend">
        {panel.series.map((series) => (
          <span key={series.key}>
            <span className="swatch is-line" style={{ background: series.color }} aria-hidden="true" />
            {series.label}
          </span>
        ))}
      </p>
      <ChartFrame
        height={HEIGHT}
        margin={margin}
        role="group"
        label={`${panel.title} against the ten length deciles of the cell-type graph, on a logarithmic axis.`}
        onPointer={(px, _py, inner) => {
          const x = linear([1, last], [0, inner.width]);
          setHover(clamp(Math.round(x.invert(px)), 1, last));
        }}
        onLeave={() => setHover(null)}
        overlay={({ width, margin: m, height }) => {
          if (!row) return null;
          const x = linear([1, last], [0, width - m.left - m.right]);
          const y = log(panel.domain, [height - m.top - m.bottom, 0]);
          const top = Math.min(...panel.series.map((series) => y(clamp(row[series.key], ...panel.domain))));
          return (
            <Tooltip x={m.left + x(row.decile)} y={m.top + top - 6} width={width}>
              <div className="tip-title">
                Decile {row.decile}, {micron(row.min_length_um)} to {micron(row.max_length_um)}
              </div>
              {panel.series.map((series) => (
                <Row
                  key={series.key}
                  label={series.label}
                  value={fixed(row[series.key], panel.digits)}
                  color={series.color}
                />
              ))}
              <Row label="Connections" value={count(row.edges)} />
              <Row label="Synapses" value={count(row.synapses)} />
            </Tooltip>
          );
        }}
      >
        {({ width, height }) => {
          const x = linear([1, last], [0, width]);
          const y = log(panel.domain, [height, 0]);
          const step = width / (last - 1);
          return (
            <g>
              <YAxis
                scale={y}
                ticks={panel.ticks}
                width={width}
                format={panel.format}
                title={panel.title}
                inset={margin.left - 4}
              />
              <XAxis
                scale={x}
                ticks={wide ? deciles.map((item) => item.decile) : [1, 5, 10]}
                height={height}
                width={width}
                margin={margin}
                format={String}
                title="Length decile, shortest first"
              />
              {panel.series.map((series) => (
                <path
                  key={series.key}
                  data-mark="line"
                  pathLength="1"
                  d={line(deciles.map((item) => [x(item.decile), y(clamp(item[series.key], ...panel.domain))]))}
                  fill="none"
                  stroke={series.color}
                  strokeWidth="2"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  strokeDasharray={series.dashed ? "4 4" : undefined}
                />
              ))}
              {deciles.map((item, i) => (
                <g
                  key={item.decile}
                  {...rowProps(item.decile)}
                  role="img"
                  aria-label={`Decile ${item.decile}, ${micron(item.min_length_um)} to ${micron(
                    item.max_length_um,
                  )}: ${reading(item)}`}
                >
                  <rect
                    className="row-band"
                    x={x(item.decile) - step / 2}
                    width={step}
                    y={0}
                    height={height}
                    rx={3}
                  />
                  {panel.series.map((series) => (
                    <circle
                      key={series.key}
                      data-mark="dot"
                      style={{ "--mark-index": i }}
                      cx={x(item.decile)}
                      cy={y(clamp(item[series.key], ...panel.domain))}
                      r={hover === item.decile ? 4.5 : 3}
                      fill={series.color}
                    />
                  ))}
                </g>
              ))}
            </g>
          );
        }}
      </ChartFrame>
    </div>
  );
}

/** The values behind the figure: every decile, and the three groups whose lengths differ most. */
export function SynapseTable({ data }) {
  const { deciles, groups, totals } = data.synapses;
  return (
    <>
      <TableWrap label="Values behind Figure 13: the ten length deciles">
        <table className="data">
          <caption>
            The {count(totals.edges)} connections sorted by length into {totals.deciles} equal groups. The expected
            rate is the mean synapse count over every connection divided by the decile&rsquo;s mean length, the rate
            the decile would show if synapse count did not depend on length at all; a decile buying its synapses at
            the going rate sits at 1.
          </caption>
          <thead>
            <tr>
              <th scope="col">Decile</th>
              <th scope="col" className="num-col">
                Length range
              </th>
              <th scope="col" className="num-col">
                Mean length
              </th>
              <th scope="col" className="num-col">
                Synapses
              </th>
              <th scope="col" className="num-col">
                Mean
              </th>
              <th scope="col" className="num-col">
                Median
              </th>
              <th scope="col" className="num-col">
                Per µm
              </th>
              <th scope="col" className="num-col">
                Observed / expected
              </th>
            </tr>
          </thead>
          <tbody>
            {deciles.map((row) => (
              <tr key={row.decile}>
                <th scope="row">{row.decile}</th>
                <td className="num-col">
                  {fixed(row.min_length_um, 0)} to {micron(row.max_length_um)}
                </td>
                <td className="num-col">{micron(row.mean_length_um)}</td>
                <td className="num-col">{count(row.synapses)}</td>
                <td className="num-col">{fixed(row.mean_synapses, 1)}</td>
                <td className="num-col">{count(row.median_synapses)}</td>
                <td className="num-col">{fixed(row.synapses_per_um, 3)}</td>
                <td className="num-col">{fixed(row.observed_over_expected, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>

      <TableWrap label="Values behind Figure 13: length against synapse count in three groups">
        <table className="data">
          <caption>
            The correlations are over every connection in the group. At this many connections a correlation this
            small still returns a p-value at the floor of double precision, which is a statement about the number of
            connections and not about the size of the effect.
          </caption>
          <thead>
            <tr>
              <th scope="col">Connections</th>
              <th scope="col" className="num-col">
                Count
              </th>
              <th scope="col" className="num-col">
                Wire
              </th>
              <th scope="col" className="num-col">
                Mean length
              </th>
              <th scope="col" className="num-col">
                Synapses
              </th>
              <th scope="col" className="num-col">
                Per µm
              </th>
              <th scope="col" className="num-col">
                Median
              </th>
              <th scope="col" className="num-col">
                ρ
              </th>
              <th scope="col" className="num-col">
                Pearson r on logs
              </th>
            </tr>
          </thead>
          <tbody>
            {GROUPS.map(([key, label]) => {
              const group = groups[key];
              return (
                <tr key={key}>
                  <th scope="row">{label}</th>
                  <td className="num-col">{count(group.edges)}</td>
                  <td className="num-col">{millimetre(group.wire_um)}</td>
                  <td className="num-col">{micron(group.mean_length_um)}</td>
                  <td className="num-col">{count(group.synapses)}</td>
                  <td className="num-col">{fixed(group.synapses_per_um, 3)}</td>
                  <td className="num-col">{count(group.median_synapses)}</td>
                  <td className="num-col">{fixed(group.correlation.spearman_rho, 3)}</td>
                  <td className="num-col">{fixed(group.correlation.pearson_log_r, 3)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </TableWrap>
    </>
  );
}
