import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis } from "../Chart.jsx";
import { useRovingRows } from "./useRovingRows.js";
import { TableWrap } from "../ui.jsx";
import { count, fixed, millimetre, percent, pValue, signed } from "../../lib/format.js";
import { useMedia } from "../../lib/hooks.js";
import { linear } from "../../lib/scales.js";

/** The two quantities a pair of neuropils can be compared on: the wire each side holds, and how economically. */
export const VIEWS = [
  { value: "wire", label: "Wire held" },
  { value: "economy", label: "Internal economy" },
];

const ROW = 17;
const STACKED_ROW = 40;

const compartmentName = (id) => (id === "vnc" ? "nerve cord" : "brain");

/** The pairs one view can draw, with the difference it plots and the scale it needs. */
export function pairsFor(data, view) {
  const pairs = data.symmetry.pairs;
  if (view === "economy") {
    return pairs
      .filter((pair) => pair.cost_ratio_left != null && pair.cost_ratio_right != null)
      .map((pair) => ({ ...pair, difference: pair.cost_ratio_left - pair.cost_ratio_right }));
  }
  return pairs.map((pair) => ({ ...pair, difference: pair.log_ratio }));
}

const VIEW = {
  wire: {
    domain: [-2.8, 2.8],
    ticks: [-2, -1, 0, 1, 2],
    title: "Natural log of the left side's wire over the right side's",
    // Stacked, the plot is too narrow to carry the full title without it running off the left edge.
    shortTitle: "Natural log of left over right wire",
    summary: (data) => data.symmetry.wire_asymmetry,
    digits: 3,
  },
  economy: {
    domain: [-0.18, 0.18],
    ticks: [-0.15, -0.075, 0, 0.075, 0.15],
    title: "Left minus right internal cost ratio",
    shortTitle: "Left minus right cost ratio",
    summary: (data) => data.symmetry.cost_ratio_asymmetry,
    digits: 4,
  },
};

export default function WireSymmetry({ data, view }) {
  const [hover, setHover] = useState(null);
  const wide = useMedia("(min-width: 700px)");
  const spec = VIEW[view];
  const rows = pairsFor(data, view);
  const summary = spec.summary(data);
  const margin = { top: 40, right: 44, bottom: 52, left: wide ? 132 : 12 };
  const step = wide ? ROW : STACKED_ROW;
  const height = margin.top + margin.bottom + rows.length * step;
  const rowProps = useRovingRows(
    rows.map((row) => row.neuropil),
    (neuropil) => setHover(neuropil == null ? null : rows.findIndex((row) => row.neuropil === neuropil)),
  );

  return (
    <ChartFrame
      height={height}
      margin={margin}
      role="group"
      label={`The ${rows.length} left-right pairs of neuropils, each at its ${spec.title.toLowerCase()}, against a line at zero.`}
      onPointer={(_x, y, inner) => {
        const index = Math.floor(y / (inner.height / rows.length));
        setHover(index >= 0 && index < rows.length ? index : null);
      }}
      onLeave={() => setHover(null)}
      overlay={({ height: inner, margin: m, width }) => {
        if (hover == null) return null;
        const row = rows[hover];
        const line = inner / rows.length;
        const x = linear(spec.domain, [0, width - m.left - m.right]);
        return (
          <Tooltip
            x={m.left + x(Math.min(Math.max(row.difference, spec.domain[0]), spec.domain[1]))}
            y={m.top + hover * line + line / 2 - 6}
            width={width}
          >
            <div className="tip-title">
              {row.neuropil}, {compartmentName(row.compartment)}
            </div>
            {view === "wire" ? (
              <>
                <Row label="Left" value={`${millimetre(row.wire_left_um)}, ${count(row.types_left)} types`} />
                <Row label="Right" value={`${millimetre(row.wire_right_um)}, ${count(row.types_right)} types`} />
                <Row
                  label="Larger side"
                  value={`${fixed(Math.exp(Math.abs(row.log_ratio)), 2)}× the other`}
                />
              </>
            ) : (
              <>
                <Row label="Left, internal cost" value={fixed(row.cost_ratio_left, 4)} />
                <Row label="Right, internal cost" value={fixed(row.cost_ratio_right, 4)} />
              </>
            )}
            <Row label="Difference" value={signed(row.difference, spec.digits)} />
          </Tooltip>
        );
      }}
    >
      {({ width, height: inner }) => {
        const x = linear(spec.domain, [0, width]);
        const line = inner / rows.length;
        const mean = x(Math.min(Math.max(summary.mean, spec.domain[0]), spec.domain[1]));
        return (
          <g>
            <XAxis
              scale={x}
              ticks={spec.ticks}
              height={inner}
              width={width}
              margin={margin}
              format={(t) => (t === 0 ? "0" : signed(t, spec.digits === 4 ? 3 : 0))}
              title={wide ? spec.title : spec.shortTitle}
            />
            {/* Two copies of one structure holding the same amount sit on this line. */}
            <line x1={x(0)} x2={x(0)} y1={-10} y2={inner} stroke="var(--rule-strong)" />
            <text className="direct-label" x={x(0)} y={-26} textAnchor="middle">
              In balance
            </text>
            {/* The mean over every pair, the quantity the sign-flip null is built for. */}
            <line x1={mean} x2={mean} y1={-4} y2={inner} stroke="var(--wire-ink)" strokeWidth="2" strokeDasharray="4 3" />
            <text className="mark-label" x={mean} y={-8} textAnchor="middle" fill="var(--wire-ink)">
              mean {signed(summary.mean, spec.digits)}
            </text>
            {rows.map((row, i) => {
              const top = i * line;
              const at = x(Math.min(Math.max(row.difference, spec.domain[0]), spec.domain[1]));
              // Stacked, the mark sits low in its band so the name above it is nearer than the next name below.
              const centre = wide ? top + line / 2 : top + line - 16;
              return (
                <g
                  key={row.neuropil}
                  {...rowProps(row.neuropil)}
                  role="img"
                  aria-label={
                    view === "wire"
                      ? `${row.neuropil}, ${compartmentName(row.compartment)}: left ${millimetre(
                          row.wire_left_um,
                        )} against right ${millimetre(row.wire_right_um)}, log ratio ${signed(row.log_ratio, 3)}`
                      : `${row.neuropil}, ${compartmentName(row.compartment)}: internal cost ${fixed(
                          row.cost_ratio_left,
                          4,
                        )} on the left against ${fixed(row.cost_ratio_right, 4)} on the right`
                  }
                >
                  <rect
                    className="row-band"
                    x={-margin.left + 2}
                    width={width + margin.left + margin.right - 4}
                    y={top + 0.5}
                    height={line - 1}
                    rx={3}
                  />
                  {wide ? (
                    <text className="row-label" x={-12} y={centre} dy="0.32em" textAnchor="end">
                      {row.neuropil}
                    </text>
                  ) : (
                    <text className="row-label" x={0} y={centre - 13}>
                      {row.neuropil}
                    </text>
                  )}
                  <line
                    x1={x(0)}
                    x2={at}
                    y1={centre}
                    y2={centre}
                    stroke={row.compartment === "vnc" ? "var(--ink-3)" : "var(--wire)"}
                    strokeWidth="1.5"
                  />
                  <circle
                    data-mark="dot"
                    style={{ "--mark-index": i }}
                    cx={at}
                    cy={centre}
                    r={hover === i ? 5 : 3.5}
                    fill={row.compartment === "vnc" ? "var(--ink-3)" : "var(--wire)"}
                  />
                </g>
              );
            })}
          </g>
        );
      }}
    </ChartFrame>
  );
}

/** The two nulls, every pair, and the neuropils that are not part of one. */
export function SymmetryTable({ data, view }) {
  const { pairs, midline, unpaired_sides: unpaired, totals, wire_asymmetry: wire, cost_ratio_asymmetry: cost } =
    data.symmetry;
  const rows = pairsFor(data, view);
  return (
    <>
      <TableWrap label="Values behind Figure 17: the three nulls">
        <table className="data">
          <caption>
            The first test is two-sided; the other two are one-sided, with p = (1 + k) / ({wire.permutations} + 1).
            Negating each pair&rsquo;s ratio at random gives the null for a systematic side bias; matching each left
            neuropil to a right neuropil drawn at random instead of to its own counterpart gives the asymmetry
            expected between two unrelated structures.
          </caption>
          <thead>
            <tr>
              <th scope="col">Test</th>
              <th scope="col" className="num-col">
                Pairs
              </th>
              <th scope="col" className="num-col">
                Observed
              </th>
              <th scope="col" className="num-col">
                Null
              </th>
              <th scope="col" className="num-col">
                z
              </th>
              <th scope="col" className="num-col">
                p
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Mean log ratio, sign-flip null</th>
              <td className="num-col">{count(wire.pairs)}</td>
              <td className="num-col">{signed(wire.mean, 3)}</td>
              <td className="num-col">0 ± {fixed(wire.null_sd, 4)}</td>
              <td className="num-col">{fixed(wire.z_score, 2)}</td>
              <td className="num-col">{pValue(wire.p_value)}</td>
            </tr>
            <tr>
              <th scope="row">Mean absolute log ratio, random matching</th>
              <td className="num-col">{count(wire.pairs)}</td>
              <td className="num-col">{fixed(wire.mean_absolute, 3)}</td>
              <td className="num-col">
                {fixed(wire.repaired_null_mean, 3)} ± {fixed(wire.repaired_null_sd, 3)}
              </td>
              <td className="num-col">—</td>
              <td className="num-col">{pValue(wire.repaired_p_value)}</td>
            </tr>
            <tr>
              <th scope="row">Mean left-minus-right internal cost, sign-flip null</th>
              <td className="num-col">{count(cost.pairs)}</td>
              <td className="num-col">{signed(cost.mean, 4)}</td>
              <td className="num-col">0 ± {fixed(cost.null_sd, 4)}</td>
              <td className="num-col">{fixed(cost.z_score, 2)}</td>
              <td className="num-col">{pValue(cost.p_value)}</td>
            </tr>
          </tbody>
        </table>
      </TableWrap>

      <TableWrap label={`Values behind Figure 17: every pair, by ${view === "wire" ? "the wire it holds" : "its internal economy"}`}>
        <table className="data">
          <caption>
            The {count(rows.length)} pairs the figure draws, largest by wire first. A dash marks a side the atlas
            left untested because it holds too few cell types or too few internal connections.
          </caption>
          <thead>
            <tr>
              <th scope="col">Neuropil</th>
              <th scope="col">Compartment</th>
              <th scope="col" className="num-col">
                Types, left / right
              </th>
              <th scope="col" className="num-col">
                Wire, left
              </th>
              <th scope="col" className="num-col">
                Wire, right
              </th>
              <th scope="col" className="num-col">
                Log ratio
              </th>
              <th scope="col" className="num-col">
                Internal cost, left / right
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.neuropil}>
                <th scope="row">{row.neuropil}</th>
                <td>{compartmentName(row.compartment)}</td>
                <td className="num-col">
                  {count(row.types_left)} / {count(row.types_right)}
                </td>
                <td className="num-col">{millimetre(row.wire_left_um)}</td>
                <td className="num-col">{millimetre(row.wire_right_um)}</td>
                <td className="num-col">{signed(row.log_ratio, 3)}</td>
                <td className="num-col">
                  {row.cost_ratio_left == null ? "—" : fixed(row.cost_ratio_left, 3)} /{" "}
                  {row.cost_ratio_right == null ? "—" : fixed(row.cost_ratio_right, 3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>

      <TableWrap label="Values behind Figure 17: the neuropils that are not part of a pair">
        <table className="data">
          <caption>
            {count(totals.midline.neuropils)} neuropils carry no hemisphere suffix and hold{" "}
            {percent(totals.midline.wire_share)} of the wire between them;{" "}
            {count(totals.unpaired_sides.neuropils)} are one side of a structure whose other side holds no cell type
            in this specimen, holding {percent(totals.unpaired_sides.wire_share, 2)} between them. Neither group is
            in the tests above, and both are listed here rather than dropped.
          </caption>
          <thead>
            <tr>
              <th scope="col">Neuropil</th>
              <th scope="col">Group</th>
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
            </tr>
          </thead>
          <tbody>
            {[
              ...midline.map((row) => ({ ...row, group: "no hemisphere suffix" })),
              ...unpaired.map((row) => ({ ...row, group: "one side only" })),
            ].map((row) => (
              <tr key={row.neuropil}>
                <th scope="row">{row.neuropil}</th>
                <td>{row.group}</td>
                <td>{compartmentName(row.compartment)}</td>
                <td className="num-col">{count(row.types)}</td>
                <td className="num-col">{millimetre(row.wire_um)}</td>
                <td className="num-col">{percent(row.wire_share, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      <p className="caption">
        The {count(totals.paired.neuropils)} paired neuropils hold {percent(totals.paired.wire_share)} of the{" "}
        {millimetre(totals.total_wire_um)} in the specimen. Wire, share, cell types and internal cost are read from
        the wire atlas rather than recomputed. The mean absolute difference between the two sides of a pair on the
        internal cost ratio is {fixed(cost.mean_absolute, 4)}, on ratios that all sit below one.
      </p>
    </>
  );
}
