import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, barPath } from "../Chart.jsx";
import { useRovingRows } from "./useRovingRows.js";
import { TableWrap } from "../ui.jsx";
import { count, micron, millimetre, percent, superclassName } from "../../lib/format.js";
import { useMedia } from "../../lib/hooks.js";
import { linear, niceTicks } from "../../lib/scales.js";

const SHOWN = 10;
const ROW = 32;

/** The classes of cell owning the most wire, in the order the result file ranks them. */
export const owners = (data, limit = SHOWN) => data.concentration.superclasses.slice(0, limit);

export default function Superclasses({ data }) {
  const [hover, setHover] = useState(null);
  const wide = useMedia("(min-width: 700px)");
  const rows = owners(data);
  const margin = { top: 34, right: 64, bottom: 46, left: wide ? 180 : 12 };
  const step = wide ? ROW : ROW + 18;
  const height = margin.top + margin.bottom + rows.length * step;
  const top = rows[0].wire_share;
  const rowProps = useRovingRows(
    rows.map((row) => row.superclass),
    (id) => setHover(id == null ? null : rows.findIndex((row) => row.superclass === id)),
  );

  return (
    <ChartFrame
      height={height}
      margin={margin}
      role="group"
      label={`Share of the wiring budget touched by each of the ${rows.length} classes of cell that own the most.`}
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
            <div className="tip-title">{superclassName(row.superclass)}</div>
            <Row label="Wire touched" value={millimetre(row.wire_um)} />
            <Row label="Share of budget" value={percent(row.wire_share)} />
            <Row label="Cell types" value={count(row.types)} />
            <Row label="Connections" value={count(row.edges)} />
            <Row label="Mean length" value={micron(row.mean_length_um)} />
            <Row label="Median length" value={micron(row.median_length_um)} />
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
              format={(t) => percent(t, 0)}
              title="Share of all wire touched"
            />
            {rows.map((row, i) => {
              const rowTop = i * rowHeight;
              const barTop = wide ? rowTop + rowHeight / 2 - 8 : rowTop + rowHeight / 2 + 2;
              const name = superclassName(row.superclass);
              return (
                <g
                  key={row.superclass}
                  {...rowProps(row.superclass)}
                  role="img"
                  aria-label={`${name}: ${percent(row.wire_share)} of the budget over ${count(
                    row.edges,
                  )} connections, mean ${micron(row.mean_length_um)}, median ${micron(row.median_length_um)}`}
                >
                  <rect
                    className="row-band"
                    x={-margin.left + 2}
                    width={width + margin.left + margin.right - 4}
                    y={rowTop + 1}
                    height={rowHeight - 2}
                    rx={3}
                  />
                  {wide ? (
                    <text className="row-label" x={-14} y={rowTop + rowHeight / 2} dy="0.32em" textAnchor="end">
                      {name}
                    </text>
                  ) : (
                    <text className="row-label" x={0} y={rowTop + rowHeight / 2 - 12}>
                      {name}
                    </text>
                  )}
                  <path
                    data-mark="bar"
                    d={barPath(0, barTop, x(row.wire_share), 16)}
                    fill="var(--wire)"
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
export function SuperclassTable({ data }) {
  const rows = data.concentration.superclasses;
  return (
    <>
      <TableWrap label="Values behind Figure 6: every class of cell by the wire it touches">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Class</th>
              <th scope="col" className="num-col">
                Cell types
              </th>
              <th scope="col" className="num-col">
                Connections
              </th>
              <th scope="col" className="num-col">
                Wire
              </th>
              <th scope="col" className="num-col">
                Share
              </th>
              <th scope="col" className="num-col">
                Mean
              </th>
              <th scope="col" className="num-col">
                Median
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.superclass}>
                <th scope="row">{superclassName(row.superclass)}</th>
                <td className="num-col">{count(row.types)}</td>
                <td className="num-col">{count(row.edges)}</td>
                <td className="num-col">{millimetre(row.wire_um)}</td>
                <td className="num-col">{percent(row.wire_share)}</td>
                <td className="num-col">{micron(row.mean_length_um)}</td>
                <td className="num-col">{micron(row.median_length_um)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      <p className="caption">
        All {count(rows.length)} classes, by the wire on connections they touch. A connection between two classes
        counts for both, so the shares add to more than one; a connection between two types of the same class
        counts once for it. Totals are over {millimetre(data.concentration.total_wire_um)} of wire.
      </p>
    </>
  );
}
