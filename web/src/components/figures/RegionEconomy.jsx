import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, YAxis, spreadLabels } from "../Chart.jsx";
import { count, fixed, millimetre, percent, times } from "../../lib/format.js";
import { linear, log, niceTicks } from "../../lib/scales.js";

/** Neuropils big enough to have been given a within-neuropil placement test, largest first. */
export const tested = (data) => data.atlas.neuropils.filter((row) => row.cost_ratio != null);

/** Regions called out on the chart: the two least economical, and the most. */
function labelled(rows) {
  const byRatio = [...rows].sort((a, b) => b.cost_ratio - a.cost_ratio);
  return [byRatio[0], byRatio[1], byRatio[byRatio.length - 1]];
}

/** One, two and five in each decade the domain covers: powers of ten alone leave this axis with two ticks. */
function decadeTicks([lo, hi]) {
  const out = [];
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e += 1) {
    for (const m of [1, 2, 5]) {
      const v = m * 10 ** e;
      if (v >= lo && v <= hi) out.push(v);
    }
  }
  return out;
}

export default function RegionEconomy({ data }) {
  const [hover, setHover] = useState(null);
  const rows = tested(data);
  const called = labelled(rows);
  const named = new Set(called.map((row) => row.neuropil));
  const wires = rows.map((row) => row.wire_um / 1000);
  const ratios = rows.map((row) => row.cost_ratio);
  const domain = [Math.min(...wires) * 0.7, Math.max(...wires) * 1.4];
  const span = [Math.min(0.4, Math.min(...ratios) - 0.05), Math.max(1.05, Math.max(...ratios) + 0.05)];
  const margin = { top: 34, right: 24, bottom: 52, left: 56 };

  return (
    <ChartFrame
      height={400}
      margin={margin}
      role="group"
      label={
        `Internal wiring cost of each of the ${rows.length} neuropils large enough to test, as a share of the ` +
        "mean of 1000 reshuffles of its own cell types, against the wire it holds."
      }
      onPointer={(px, py, inner) => {
        const x = log(domain, [0, inner.width]);
        const y = linear(span, [inner.height, 0]);
        let best = null;
        rows.forEach((row, i) => {
          const d = Math.hypot(x(wires[i]) - px, y(row.cost_ratio) - py);
          if (d < 22 && (!best || d < best.d)) best = { i, d };
        });
        setHover(best?.i ?? null);
      }}
      onLeave={() => setHover(null)}
      overlay={({ width, height, margin: m }) => {
        if (hover == null) return null;
        const row = rows[hover];
        const x = log(domain, [0, width]);
        const y = linear(span, [height, 0]);
        return (
          <Tooltip x={m.left + x(wires[hover])} y={m.top + y(row.cost_ratio) - 10} width={width + m.left + m.right}>
            <div className="tip-title">{row.neuropil}</div>
            <Row label="Wire held" value={millimetre(row.wire_um)} />
            <Row label="Its own connections" value={count(row.edges_internal)} />
            <Row label="Internal cost" value={millimetre(row.internal_real_um)} />
            <Row label="Reshuffled mean" value={millimetre(row.internal_null_mean_um)} />
            <Row label="Ratio" value={times(row.cost_ratio, 3)} />
            <Row label="z" value={fixed(row.z_score, 1)} />
            <Row
              label="At or below real"
              value={`${count(row.n_at_or_below_real)} of ${count(data.atlas.totals.permutations)}`}
            />
          </Tooltip>
        );
      }}
    >
      {({ width, height }) => {
        const x = log(domain, [0, width]);
        const y = linear(span, [height, 0]);
        return (
          <g>
            <YAxis
              scale={y}
              ticks={niceTicks(span, 5)}
              width={width}
              format={(t) => t.toFixed(1)}
              title="Internal cost as a share of its own reshuffled mean"
            />
            <XAxis
              scale={x}
              ticks={decadeTicks(domain)}
              height={height}
              width={width}
              format={String}
              title="Wire held (mm, log scale)"
            />
            {/* A region no better placed than chance against its own positions would sit on this line. */}
            <line x1={0} x2={width} y1={y(1)} y2={y(1)} stroke="var(--rule-strong)" strokeDasharray="3 3" />
            <text className="direct-label" x={width} y={y(1) - 8} textAnchor="end">
              Reshuffled within the region
            </text>

            {rows.map((row, i) => (
              <circle
                key={row.neuropil}
                cx={x(wires[i])}
                cy={y(row.cost_ratio)}
                r={hover === i ? 7 : 5}
                fill={row.compartment === "vnc" ? "var(--ink-3)" : "var(--wire)"}
                stroke="var(--paper)"
                strokeWidth="2"
                opacity={hover === i || named.has(row.neuropil) ? 1 : 0.78}
              />
            ))}

            {/* The two antennal lobes all but coincide, so their labels stack rather than overprint each other. */}
            {spreadLabels(
              called.map((row) => ({
                key: row.neuropil,
                cx: x(row.wire_um / 1000),
                y: y(row.cost_ratio) - 14,
              })),
              15,
              10,
              height,
            ).map(({ key, cx, y: ly }) => (
              <text className="mark-label" key={key} x={cx} y={ly} textAnchor="middle">
                {key}
              </text>
            ))}
          </g>
        );
      }}
    </ChartFrame>
  );
}

/** The regions at each end of the economy ranking, so the exception is reachable without a pointer. */
export function EconomyTable({ data }) {
  const rows = [...tested(data)].sort((a, b) => a.cost_ratio - b.cost_ratio);
  const ends = [...rows.slice(0, 6), ...rows.slice(-6)];
  const permutations = data.atlas.totals.permutations;
  const weak = rows.filter((row) => row.n_at_or_below_real > permutations * 0.05);

  return (
    <>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Neuropil</th>
              <th scope="col" className="num-col">
                Its own connections
              </th>
              <th scope="col" className="num-col">
                Internal cost
              </th>
              <th scope="col" className="num-col">
                Reshuffled mean
              </th>
              <th scope="col" className="num-col">
                Ratio
              </th>
              <th scope="col" className="num-col">
                z
              </th>
              <th scope="col" className="num-col">
                At or below real
              </th>
            </tr>
          </thead>
          <tbody>
            {ends.map((row, i) => (
              <tr key={row.neuropil} className={i === 6 ? "row-gap" : undefined}>
                <th scope="row">{row.neuropil}</th>
                <td className="num-col">{count(row.edges_internal)}</td>
                <td className="num-col">{millimetre(row.internal_real_um)}</td>
                <td className="num-col">{millimetre(row.internal_null_mean_um)}</td>
                <td className="num-col">{fixed(row.cost_ratio, 3)}</td>
                <td className="num-col">{fixed(row.z_score, 1)}</td>
                <td className="num-col">
                  {count(row.n_at_or_below_real)} / {count(permutations)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="caption">
        The six most and six least economical of the {count(rows.length)} neuropils large enough to test. The
        reshuffle moves cell types only between positions inside the same neuropil, so it asks whether a region is
        laid out economically given where its own cells already sit. {count(weak.length)} of {count(rows.length)}{" "}
        regions are not cheaper than at least {percent(0.05, 0)} of their own reshuffles.
      </p>
    </>
  );
}
