import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, barPath } from "../Chart.jsx";
import { count, fixed, millimetre, percent, times } from "../../lib/format.js";
import { useMedia } from "../../lib/hooks.js";
import { linear, niceTicks } from "../../lib/scales.js";

const SHOWN = 14;
const ROW = 32;

const compartmentName = (id) => (id === "vnc" ? "nerve cord" : "brain");

/** The neuropils holding the most wire, in the order the result file ranks them. */
export const ranked = (data, limit = SHOWN) => data.atlas.neuropils.slice(0, limit);

export default function WireAtlas({ data }) {
  const [hover, setHover] = useState(null);
  const wide = useMedia("(min-width: 700px)");
  const rows = ranked(data);
  const margin = { top: 34, right: 64, bottom: 46, left: wide ? 152 : 12 };
  const step = wide ? ROW : ROW + 18;
  const height = margin.top + margin.bottom + rows.length * step;
  const top = rows[0].wire_share;

  return (
    <ChartFrame
      height={height}
      margin={margin}
      role="group"
      label={`Share of the wiring budget held by each of the ${rows.length} neuropils that hold the most of it.`}
      onPointer={(x, y, inner) => {
        const rowHeight = inner.height / rows.length;
        const index = Math.floor(y / rowHeight);
        setHover(index >= 0 && index < rows.length ? index : null);
      }}
      onLeave={() => setHover(null)}
      overlay={({ height: inner, margin: m, width }) => {
        if (hover == null) return null;
        const row = rows[hover];
        const rowHeight = inner / rows.length;
        return (
          <Tooltip
            x={m.left + ((width - m.left - m.right) * row.wire_share) / (top * 1.08)}
            y={m.top + hover * rowHeight + rowHeight / 2 - 6}
            width={width}
          >
            <div className="tip-title">
              {row.neuropil}, {compartmentName(row.compartment)}
            </div>
            <Row label="Wire held" value={millimetre(row.wire_um)} />
            <Row label="Share of budget" value={percent(row.wire_share)} />
            <Row label="Cell types" value={count(row.types)} />
            <Row label="Connection ends" value={count(row.edges_incident)} />
            {row.cost_ratio != null && <Row label="Internal cost / reshuffled" value={times(row.cost_ratio, 3)} />}
          </Tooltip>
        );
      }}
    >
      {({ width, height: inner }) => {
        const x = linear([0, top * 1.08], [0, width]);
        const rowHeight = inner / rows.length;
        return (
          <g>
            <XAxis
              scale={x}
              ticks={niceTicks([0, top * 1.08], 5)}
              height={inner}
              width={width}
              format={(t) => percent(t, t === 0 ? 0 : 1)}
              title="Share of all wire"
            />
            {rows.map((row, i) => {
              const rowTop = i * rowHeight;
              const barTop = wide ? rowTop + rowHeight / 2 - 8 : rowTop + rowHeight / 2 + 2;
              const label = wide ? row.neuropil : `${row.neuropil} (${compartmentName(row.compartment)})`;
              return (
                <g key={row.neuropil}>
                  {wide ? (
                    <text className="row-label" x={-14} y={rowTop + rowHeight / 2} dy="0.32em" textAnchor="end">
                      {label}
                    </text>
                  ) : (
                    <text className="row-label" x={0} y={rowTop + rowHeight / 2 - 12}>
                      {label}
                    </text>
                  )}
                  <path
                    data-mark="bar"
                    d={barPath(0, barTop, x(row.wire_share), 16)}
                    fill={row.compartment === "vnc" ? "var(--ink-3)" : "var(--wire)"}
                    opacity={hover === i ? 1 : 0.9}
                  />
                  <text className="mark-label" x={x(row.wire_share) + 8} y={barTop + 12}>
                    {percent(row.wire_share)}
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

/** The table behind the figure, so every value is reachable without a pointer. */
export function AtlasTable({ data }) {
  const rows = ranked(data, 20);
  const totals = data.atlas.totals;
  return (
    <>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Neuropil</th>
              <th scope="col">Compartment</th>
              <th scope="col" className="num-col">
                Cell types
              </th>
              <th scope="col" className="num-col">
                Wire
              </th>
              <th scope="col" className="num-col">
                Share
              </th>
              <th scope="col" className="num-col">
                Internal cost / reshuffled
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.neuropil}>
                <th scope="row">{row.neuropil}</th>
                <td>{compartmentName(row.compartment)}</td>
                <td className="num-col">{count(row.types)}</td>
                <td className="num-col">{millimetre(row.wire_um)}</td>
                <td className="num-col">{percent(row.wire_share)}</td>
                <td className="num-col">{row.cost_ratio == null ? "—" : fixed(row.cost_ratio, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="caption">
        The twenty neuropils holding the most wire, of {count(totals.neuropils_with_types)} that hold any. A
        connection lends half its length to the neuropil nearest each of its ends, so the shares add to one across
        all {count(totals.neuropils_with_types)}. A dash marks a neuropil too small for a placement test, which
        needs at least 12 cell types and 50 connections of its own.
      </p>
    </>
  );
}
