import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, YAxis } from "../Chart.jsx";
import { TableWrap } from "../ui.jsx";
import { count, fixed, pValue, percent } from "../../lib/format.js";
import { linear, niceTicks } from "../../lib/scales.js";

const METRICS = [
  { key: "flow", label: "All sensory-to-motor flow", intact: "flow" },
  { key: "flow_brain_to_vnc", label: "Brain sensory to nerve-cord motor", intact: "flow_brain_to_vnc" },
  { key: "flow_vnc_to_brain", label: "Nerve-cord sensory to brain motor", intact: "flow_vnc_to_brain" },
];

function Histogram({ metric, result, intact, cut, marks }) {
  const [hover, setHover] = useState(null);
  const edges = result.null.edges;
  const counts = result.null.counts;
  // Padded by a share of the span, not of the values, so a mark far below the histogram still stands clear of the edge.
  const low = Math.min(edges[0], cut, ...marks.map((m) => m.value));
  const high = Math.max(edges[edges.length - 1], cut, ...marks.map((m) => m.value));
  const pad = (high - low) * 0.06;
  const lo = low - pad;
  const hi = high + pad;

  // Everything above the plot is stacked on 16px lines: the panel name, what the cut costs as a share of the
  // intact graph, then the cut's own rule and each dashed mark, so no two of them share a baseline.
  const top = 62 + marks.length * 16;

  return (
    <ChartFrame
      height={top + 172}
      margin={{ top, right: 20, bottom: 46, left: 56 }}
      role="group"
      label={`${metric.label}: how much flow 1000 random sets of ordinary connections of the same total length remove, and how much cutting the neck removes.`}
      onPointer={(px, _py, inner) => {
        const x = linear([lo, hi], [0, inner.width]);
        const value = x.invert(px);
        const index = counts.findIndex((_, i) => value >= edges[i] && value < edges[i + 1]);
        setHover(index >= 0 ? index : null);
      }}
      onLeave={() => setHover(null)}
      overlay={({ width, margin }) => {
        if (hover == null) return null;
        const inner = width - margin.left - margin.right;
        const x = linear([lo, hi], [0, inner]);
        return (
          <Tooltip x={margin.left + x((edges[hover] + edges[hover + 1]) / 2)} y={margin.top + 6} width={width}>
            <div className="tip-title">
              {count(edges[hover])} to {count(edges[hover + 1])} lost
            </div>
            <Row label="Random sets" value={count(counts[hover])} color="var(--null)" />
          </Tooltip>
        );
      }}
    >
      {({ width, height }) => {
        const x = linear([lo, hi], [0, width]);
        const yMax = Math.max(...counts);
        const y = linear([0, yMax], [height, 0]);
        // Every rule gets a line of its own above the plot and rises only to it. The labels all run away from
        // the same edge, and the stack is ordered from that edge outwards, so no rule crosses a label below it.
        const fromLeft = x(cut) < width / 2;
        const stack = [...marks, { value: cut, label: `Cutting the neck: ${count(cut)}`, cut: true }].sort((a, b) =>
          fromLeft ? a.value - b.value : b.value - a.value,
        );
        return (
          <g>
            <text className="axis-title" x={-48} y={16 - top}>
              {metric.label}
            </text>
            <text className="mark-label" x={width} y={32 - top} textAnchor="end">
              {percent(cut / intact, 0)} of {count(intact)} intact
            </text>
            <YAxis scale={y} ticks={niceTicks([0, yMax], 5, { integer: true })} width={width} format={count} />
            <XAxis
              scale={x}
              ticks={niceTicks([lo, hi], 5, { integer: true })}
              height={height}
              width={width}
              format={count}
              title="Flow capacity removed"
            />
            {counts.map((value, i) => {
              const left = x(edges[i]);
              const right = x(edges[i + 1]);
              return (
                <rect
                  key={edges[i]}
                  data-mark="column"
                  x={left}
                  y={y(value)}
                  width={Math.max(1, right - left - 2)}
                  height={height - y(value)}
                  fill="var(--null)"
                  opacity={hover === i ? 1 : 0.75}
                />
              );
            })}
            {stack.map((mark, i) => {
              const line = stack.length - 1 - i;
              return (
                <g key={mark.label}>
                  <line
                    x1={x(mark.value)}
                    x2={x(mark.value)}
                    y1={-8 - line * 16}
                    y2={height}
                    stroke={mark.cut ? "var(--wire)" : "var(--ink-3)"}
                    strokeWidth={mark.cut ? 2.5 : 1.5}
                    strokeDasharray={mark.cut ? undefined : "4 3"}
                  />
                  <text
                    className="mark-label"
                    x={fromLeft ? x(mark.value) + 6 : x(mark.value) - 6}
                    y={-12 - line * 16}
                    textAnchor={fromLeft ? "start" : "end"}
                    fill={mark.cut ? "var(--wire-ink)" : undefined}
                  >
                    {mark.label}
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

export default function ValueNulls({ data }) {
  const family = data.value.families.crossing_cost;
  const countMatched = data.value.families.crossing_count;
  const longest = data.value.intact.flow - data.value.real.longest.flow;

  return (
    <div className="panels">
      {METRICS.map((metric) => (
        <Histogram
          key={metric.key}
          metric={metric}
          result={family[metric.key]}
          intact={data.value.intact[metric.intact]}
          cut={family[metric.key].real}
          marks={
            metric.key === "flow"
              ? [
                  { label: `Equal count: ${count(countMatched.flow.null_mean)}`, value: countMatched.flow.null_mean },
                  { label: `Longest ordinary: ${count(longest)}`, value: longest },
                ]
              : []
          }
        />
      ))}
    </div>
  );
}

export function ValueTable({ data }) {
  const family = data.value.families.crossing_cost;
  const countMatched = data.value.families.crossing_count;
  const longest = data.value.intact.flow - data.value.real.longest.flow;
  const rows = [
    [
      "all flow, equal length (primary)",
      family.flow.real,
      family.flow.null_mean,
      family.flow.ratio,
      family.flow.p_value,
    ],
    [
      "brain sensory to nerve-cord motor, equal length",
      family.flow_brain_to_vnc.real,
      family.flow_brain_to_vnc.null_mean,
      family.flow_brain_to_vnc.ratio,
      family.flow_brain_to_vnc.p_value,
    ],
    [
      "nerve-cord sensory to brain motor, equal length",
      family.flow_vnc_to_brain.real,
      family.flow_vnc_to_brain.null_mean,
      family.flow_vnc_to_brain.ratio,
      family.flow_vnc_to_brain.p_value,
    ],
    [
      "all flow, equal connection count",
      countMatched.flow.real,
      countMatched.flow.null_mean,
      countMatched.flow.ratio,
      countMatched.flow.p_value,
    ],
    ["all flow, longest ordinary connections", family.flow.real, longest, family.flow.real / longest, null],
  ];
  return (
    <>
      <TableWrap label="Values behind Figure 9: the neck against each matched comparison">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Comparison</th>
              <th scope="col" className="num-col">
                Flow lost, neck
              </th>
              <th scope="col" className="num-col">
                Flow lost, comparison
              </th>
              <th scope="col" className="num-col">
                Ratio
              </th>
              <th scope="col" className="num-col">
                p
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, real, nullMean, ratio, p]) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                <td className="num-col">{count(real)}</td>
                <td className="num-col">{count(nullMean)}</td>
                <td className="num-col">{fixed(ratio, 2)}</td>
                <td className="num-col">{p == null ? "" : pValue(p)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      <p className="caption">
        No sensory-motor pair is disconnected by the cut. The length-matched sets hold about{" "}
        {count(data.value.removal_sets.longest_non_connective.edges)} shorter connections each, against the{" "}
        {count(data.value.removal_sets.crossing.edges)} that cross the neck, drawn from{" "}
        {count(data.value.removal_sets.non_connective_candidates.edges)} candidates. Silencing every connection of the
        descending and ascending types, not only the neck-crossing ones, removes{" "}
        {count(data.value.intact.flow_brain_to_vnc - data.value.real.incident.flow_brain_to_vnc)} of the{" "}
        {count(data.value.intact.flow_brain_to_vnc)} units from brain to nerve cord.
      </p>
    </>
  );
}
