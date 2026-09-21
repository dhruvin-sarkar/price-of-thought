import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, barPath } from "../Chart.jsx";
import { useRovingRows } from "./useRovingRows.js";
import { TableWrap } from "../ui.jsx";
import { count, micron, percent } from "../../lib/format.js";
import { useMedia } from "../../lib/hooks.js";
import { linear } from "../../lib/scales.js";

const GROUP = 92;
const BAR = 17;

const LABELS = {
  "neck-crossing": "Crossing the neck",
  "connective-incident": "Any descending or ascending connection",
  "high-degree-incident": "Touching a hub",
  "none of these": "None of these",
};

const MEASURES = [
  { key: "edge_share", label: "share of connections", color: "var(--ink-3)" },
  { key: "cost_share", label: "share of wire", color: "var(--wire)" },
];

/** A group's name, with the degree that defines the hub group spelled out. */
const groupName = (row, threshold) =>
  `${LABELS[row.label]}${row.label === "high-degree-incident" ? ` (degree ${threshold} or more)` : ""}`;

export default function CostShare({ data }) {
  const [hover, setHover] = useState(null);
  // Below this the name and the counts cannot share a line, so the counts take one of their own.
  const wide = useMedia("(min-width: 700px)");
  const rows = data.cost_share.rows;
  const threshold = data.cost_share.degree_threshold;
  const margin = { top: 34, right: 24, bottom: 46, left: 12 };
  const group = wide ? GROUP : GROUP + 16;
  const height = margin.top + margin.bottom + rows.length * group;
  const rowProps = useRovingRows(
    rows.map((row) => row.label),
    (label) => setHover(label == null ? null : rows.findIndex((row) => row.label === label)),
  );

  return (
    <ChartFrame
      height={height}
      margin={margin}
      role="group"
      label="Share of all connections and share of total wiring length, for four overlapping groups of connections."
      onPointer={(_x, y, inner) => {
        const index = Math.floor(y / (inner.height / rows.length));
        setHover(index >= 0 && index < rows.length ? index : null);
      }}
      onLeave={() => setHover(null)}
      overlay={({ height: inner, margin: m, width }) => {
        if (hover == null) return null;
        const row = rows[hover];
        const step = inner / rows.length;
        return (
          <Tooltip x={width / 2} y={m.top + hover * step + step / 2} width={width}>
            <div className="tip-title">{LABELS[row.label]}</div>
            <Row label="Connections" value={count(row.edges)} />
            <Row label="Share of connections" value={percent(row.edge_share)} color="var(--ink-3)" />
            <Row label="Share of wire" value={percent(row.cost_share)} color="var(--wire)" />
            <Row label="Mean length" value={micron(row.mean_length_um)} />
          </Tooltip>
        );
      }}
    >
      {({ width, height: inner }) => {
        const x = linear([0, 0.55], [0, width]);
        const step = inner / rows.length;
        return (
          <g>
            <XAxis
              scale={x}
              ticks={[0, 0.1, 0.2, 0.3, 0.4, 0.5]}
              height={inner}
              width={width}
              format={(t) => `${Math.round(t * 100)}%`}
              title="Share of the whole graph"
            />
            {rows.map((row, i) => {
              const top = i * step;
              const counts = `${count(row.edges)} connections, mean ${micron(row.mean_length_um)}`;
              return (
                <g
                  key={row.label}
                  {...rowProps(row.label)}
                  role="img"
                  aria-label={`${groupName(row, threshold)}: ${percent(row.edge_share)} of connections, ${percent(
                    row.cost_share,
                  )} of the wire, ${counts}`}
                >
                  <rect
                    className="row-band"
                    x={-margin.left + 2}
                    width={width + margin.left + margin.right - 4}
                    y={top + 1}
                    height={step - 2}
                    rx={3}
                  />
                  <text className="group-label" x={0} y={top + 12}>
                    {groupName(row, threshold)}
                  </text>
                  {wide ? (
                    <text className="mark-label" x={width} y={top + 12} textAnchor="end">
                      {counts}
                    </text>
                  ) : (
                    <text className="mark-label" x={0} y={top + 28}>
                      {counts}
                    </text>
                  )}
                  {MEASURES.map((measure, m) => {
                    // A 2px gap of page between the two bars, so the pair reads as one group of two marks.
                    const y = top + (wide ? 26 : 42) + m * (BAR + 2);
                    return (
                      <g key={measure.key}>
                        <path data-mark="bar" d={barPath(0, y, x(row[measure.key]), BAR)} fill={measure.color} />
                        <text className="mark-label" x={x(row[measure.key]) + 8} y={y + BAR - 4}>
                          {percent(row[measure.key])}
                        </text>
                      </g>
                    );
                  })}
                </g>
              );
            })}
          </g>
        );
      }}
    </ChartFrame>
  );
}

export function CostShareTable({ data }) {
  return (
    <TableWrap label="Values behind Figure 7: the four groups of connections">
      <table className="data">
        <caption>The first three groups overlap; the last holds the connections in none of them.</caption>
        <thead>
          <tr>
            <th scope="col">Connections</th>
            <th scope="col" className="num-col">
              Count
            </th>
            <th scope="col" className="num-col">
              Share of connections
            </th>
            <th scope="col" className="num-col">
              Share of wire
            </th>
            <th scope="col" className="num-col">
              Mean length
            </th>
          </tr>
        </thead>
        <tbody>
          {data.cost_share.rows.map((row) => (
            <tr key={row.label}>
              <th scope="row">{LABELS[row.label]}</th>
              <td className="num-col">{count(row.edges)}</td>
              <td className="num-col">{percent(row.edge_share)}</td>
              <td className="num-col">{percent(row.cost_share)}</td>
              <td className="num-col">{micron(row.mean_length_um)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}
