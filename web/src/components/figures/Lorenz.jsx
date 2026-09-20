import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, YAxis } from "../Chart.jsx";
import { count, fixed, micron, millimetre, percent, pValue, signed } from "../../lib/format.js";
import { line, linear, nearestIndex } from "../../lib/scales.js";

/** The four sets of connections the concentration is measured over, with the colours Figure 2 uses. */
const SERIES = [
  { key: "all", label: "All connections", color: "var(--wire)" },
  { key: "within the brain", label: "Brain", color: "var(--ink)" },
  { key: "within the nerve cord", label: "Nerve cord", color: "var(--null)" },
  { key: "across the neck", label: "Across the neck", color: "var(--ink-3)" },
];

const ALTERNATIVES = [
  ["lognormal", "Lognormal"],
  ["exponential", "Exponential"],
  ["truncated_power_law", "Truncated power law"],
];

const TICKS = [0, 0.25, 0.5, 0.75, 1];

export default function Lorenz({ data }) {
  const [hover, setHover] = useState(null);
  const curves = SERIES.map((series) => ({ ...series, curve: data.concentration.lorenz[series.key] })).filter(
    (series) => series.curve,
  );
  // Brain and nerve cord run within a percent of each other over most of their length, so the series are named
  // in a legend: direct labels on four curves that converge would have to sit on top of the curves themselves.
  const margin = { top: 34, right: 30, bottom: 52, left: 56 };

  return (
    <>
      <p className="legend">
        {curves.map(({ key, label, color }) => (
          <span key={key}>
            <span className="swatch is-line" style={{ background: color }} aria-hidden="true" />
            {label}
          </span>
        ))}
      </p>
      <ChartFrame
        height={420}
        margin={margin}
        role="group"
        label={
          "Cumulative share of the wiring budget against the cumulative share of connections, longest first, for " +
          `${curves.length} sets of connections. A set whose wire were spread evenly would lie on the diagonal.`
        }
        onPointer={(px, _py, inner) => {
          const x = linear([0, 1], [0, inner.width]);
          setHover(Math.min(1, Math.max(0, x.invert(px))));
        }}
        onLeave={() => setHover(null)}
        overlay={({ width, margin: m }) => {
          if (hover == null) return null;
          const x = linear([0, 1], [0, width]);
          return (
            <Tooltip x={m.left + x(hover)} y={m.top + 4} width={width + m.left + m.right}>
              <div className="tip-title">Longest {percent(hover)} of connections</div>
              {curves.map(({ key, label, color, curve }) => {
                const i = nearestIndex(curve.connection_share, hover);
                return <Row key={key} label={label} value={percent(curve.wire_share[i])} color={color} />;
              })}
            </Tooltip>
          );
        }}
      >
        {({ width, height }) => {
          const x = linear([0, 1], [0, width]);
          const y = linear([0, 1], [height, 0]);
          return (
            <g>
              <YAxis
                scale={y}
                ticks={TICKS}
                width={width}
                format={(t) => percent(t, 0)}
                title="Share of the wiring budget"
              />
              <XAxis
                scale={x}
                ticks={TICKS}
                height={height}
                width={width}
                format={(t) => percent(t, 0)}
                title="Share of connections, longest first"
              />
              {/* A budget spread evenly over its connections would follow this line. */}
              <line x1={0} y1={height} x2={width} y2={0} stroke="var(--rule-strong)" strokeDasharray="3 3" />
              <text className="direct-label" x={width * 0.74} y={y(0.74) + 20} textAnchor="start">
                Spread evenly
              </text>

              {hover != null && <line x1={x(hover)} x2={x(hover)} y1={0} y2={height} stroke="var(--rule-strong)" strokeWidth="1" />}

              {curves.map(({ key, color, curve }) => (
                <path
                  key={key}
                  data-mark="line"
                  pathLength="1"
                  d={line(curve.connection_share.map((share, i) => [x(share), y(curve.wire_share[i])]))}
                  fill="none"
                  stroke={color}
                  strokeWidth="2"
                  strokeLinejoin="round"
                />
              ))}

            </g>
          );
        }}
      </ChartFrame>
    </>
  );
}

/** The concentration of each set, and how the fitted tail fares against its alternatives. */
export function TailTable({ data }) {
  const { lorenz, lengths, tail } = data.concentration;
  return (
    <>
      <div className="table-wrap">
        <table className="data">
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
                Median
              </th>
              <th scope="col" className="num-col">
                Gini
              </th>
              <th scope="col" className="num-col">
                Longest 1% hold
              </th>
              <th scope="col" className="num-col">
                Longest 10% hold
              </th>
            </tr>
          </thead>
          <tbody>
            {SERIES.filter(({ key }) => lorenz[key]).map(({ key, label }) => (
              <tr key={key}>
                <th scope="row">{label}</th>
                <td className="num-col">{count(lengths[key].edges)}</td>
                <td className="num-col">{millimetre(lengths[key].wire_um)}</td>
                <td className="num-col">{micron(lengths[key].median_um)}</td>
                <td className="num-col">{fixed(lorenz[key].gini, 3)}</td>
                <td className="num-col">{percent(lorenz[key].top_shares["0.01"])}</td>
                <td className="num-col">{percent(lorenz[key].top_shares["0.1"])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Power law against</th>
              <th scope="col" className="num-col">
                Log-likelihood ratio
              </th>
              <th scope="col" className="num-col">
                p
              </th>
              <th scope="col">Favours</th>
            </tr>
          </thead>
          <tbody>
            {ALTERNATIVES.map(([key, label]) => {
              const test = tail.comparisons[key];
              let favours = "neither";
              if (test.p_value < 0.05) favours = test.loglikelihood_ratio > 0 ? "power law" : label.toLowerCase();
              return (
                <tr key={key}>
                  <th scope="row">{label}</th>
                  <td className="num-col">{signed(test.loglikelihood_ratio, 2)}</td>
                  <td className="num-col">{pValue(test.p_value)}</td>
                  <td>{favours}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="caption">
        The tail fit takes the {count(tail.tail_edges)} connections longer than {micron(tail.xmin_um)}, the lower
        bound that minimises the distance between the fitted and the observed distribution, and gives an exponent
        of {fixed(tail.alpha, 2)}. A positive ratio favours the power law. It is not the best account of the tail:
        a lognormal and a truncated power law both describe these lengths better.
      </p>
    </>
  );
}
