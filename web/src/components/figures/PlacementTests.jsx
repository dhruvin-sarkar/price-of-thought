import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, barPath } from "../Chart.jsx";
import { count, fixed, millimetre, pValue, percent, times } from "../../lib/format.js";
import { useMedia } from "../../lib/hooks.js";
import { linear } from "../../lib/scales.js";

const ROW = 46;

/** The six permutation tests, in the order the README lists them. */
export function rows(data) {
  return [
    ["soma positions, all nodes shuffled", data.placement.primary, "primary"],
    ["synapse-weighted cost", data.placement.weighted],
    ["shuffled within brain or nerve cord", data.placement.within_compartment],
    ["synapse centroids as positions", data.placement.synapse_positions],
    ["brain connections only", data.compartment_optimality.brain],
    ["nerve-cord connections only", data.compartment_optimality.vnc],
  ].map(([label, result, kind]) => ({ label, result, kind }));
}

export default function PlacementTests({ data }) {
  const [hover, setHover] = useState(null);
  const wide = useMedia("(min-width: 700px)");
  const tests = rows(data);
  const swapped = data.placement.primary.cost_ratio * (1 - data.swaps.reduction);
  const margin = { top: 34, right: 56, bottom: 46, left: wide ? 232 : 12 };
  const step = wide ? ROW : ROW + 20;
  const height = margin.top + margin.bottom + tests.length * step;

  return (
    <ChartFrame
      height={height}
      margin={margin}
      role="group"
      label="Wiring cost of the real placement as a share of the mean of 1000 random placements, for six tests."
      onPointer={(x, y, inner) => {
        const rowHeight = inner.height / tests.length;
        const index = Math.floor(y / rowHeight);
        setHover(index >= 0 && index < tests.length ? { index } : null);
      }}
      onLeave={() => setHover(null)}
      overlay={({ height: inner, margin: m, width }) => {
        if (!hover) return null;
        const test = tests[hover.index];
        const rowHeight = inner / tests.length;
        return (
          <Tooltip
            x={m.left + (width - m.left - m.right) * test.result.cost_ratio}
            y={m.top + hover.index * rowHeight + rowHeight / 2 - 6}
            width={width}
          >
            <div className="tip-title">{test.label}</div>
            <Row label="Real" value={millimetre(test.result.real)} />
            <Row label="Permuted mean" value={millimetre(test.result.null_mean)} />
            <Row label="Ratio" value={times(test.result.cost_ratio, 3)} />
            <Row label="z" value={fixed(test.result.z_score, 1)} />
            <Row
              label="At or below real"
              value={`${count(test.result.n_at_or_below_real)} of ${count(test.result.n_permutations)}`}
            />
          </Tooltip>
        );
      }}
    >
      {({ width, height: inner }) => {
        const x = linear([0, 1.08], [0, width]);
        const rowHeight = inner / tests.length;
        return (
          <g>
            <XAxis
              scale={x}
              ticks={[0, 0.25, 0.5, 0.75, 1]}
              height={inner}
              width={width}
              format={(t) => (t === 1 ? "1.0" : t.toFixed(2))}
              title="Cost as a share of the permuted mean"
            />
            {/* Random placement is the baseline every bar is read against. */}
            <line x1={x(1)} x2={x(1)} y1={-10} y2={inner} stroke="var(--rule-strong)" strokeDasharray="3 3" />
            <text className="direct-label" x={x(1)} y={-18} textAnchor="end">
              Random placement
            </text>

            {tests.map((test, i) => {
              const top = i * rowHeight;
              const barTop = wide ? top + rowHeight / 2 - 9 : top + rowHeight / 2 + 2;
              const active = hover?.index === i;
              const name = `${test.label}${test.kind === "primary" ? " (primary)" : ""}`;
              return (
                <g key={test.label}>
                  {wide ? (
                    <text className="row-label" x={-14} y={top + rowHeight / 2} dy="0.32em" textAnchor="end">
                      {name}
                    </text>
                  ) : (
                    <text className="row-label" x={0} y={top + rowHeight / 2 - 14}>
                      {name}
                    </text>
                  )}
                  <path
                    data-mark="bar"
                    d={barPath(0, barTop, x(test.result.cost_ratio), 18)}
                    fill={test.kind === "primary" ? "var(--wire)" : "var(--ink-3)"}
                    opacity={active ? 1 : 0.9}
                  />
                  <text className="mark-label" x={x(test.result.cost_ratio) + 8} y={barTop + 13}>
                    {fixed(test.result.cost_ratio, 3)}
                  </text>
                </g>
              );
            })}

            {/* Where cost-reducing swaps take the primary layout: a lower bound on how far from optimal it is. */}
            <g>
              <line
                x1={x(swapped)}
                x2={x(swapped)}
                y1={rowHeight * 0.2}
                y2={rowHeight * 0.86}
                stroke="var(--wire-ink)"
                strokeWidth="2"
              />
              <text className="mark-label" x={x(swapped)} y={rowHeight * 0.1} textAnchor="middle" fill="var(--wire-ink)">
                {fixed(swapped, 3)} after swaps
              </text>
            </g>
          </g>
        );
      }}
    </ChartFrame>
  );
}

/** The table behind the figure, so every value is reachable without a pointer. */
export function PlacementTable({ data }) {
  return (
    <>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Analysis</th>
              <th scope="col" className="num-col">
                Real / permuted
              </th>
              <th scope="col" className="num-col">
                z
              </th>
              <th scope="col" className="num-col">
                At or below real
              </th>
              <th scope="col" className="num-col">
                p
              </th>
            </tr>
          </thead>
          <tbody>
            {rows(data).map(({ label, result, kind }) => (
              <tr key={label}>
                <th scope="row">{`${label}${kind === "primary" ? " (primary)" : ""}`}</th>
                <td className="num-col">{fixed(result.cost_ratio, 3)}</td>
                <td className="num-col">{fixed(result.z_score, 1)}</td>
                <td className="num-col">
                  {count(result.n_at_or_below_real)} / {count(result.n_permutations)}
                </td>
                <td className="num-col">{pValue(result.p_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="caption">
        The real placement costs {millimetre(data.swaps.start_cost)} of wire. Of {count(data.swaps.proposals)} proposed
        swaps, {count(data.swaps.accepted)} lowered the cost, together to {millimetre(data.swaps.final_cost)}, a saving
        of {percent(data.swaps.reduction)}. The search had not converged, and it ignores every physical constraint on
        where cell bodies and neuropils can lie.
      </p>
    </>
  );
}
