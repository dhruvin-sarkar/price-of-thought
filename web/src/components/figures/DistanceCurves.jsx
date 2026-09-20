import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, YAxis, spreadLabels } from "../Chart.jsx";
import { fixed, micron } from "../../lib/format.js";
import { line, linear, log, logTicks, nearestIndex } from "../../lib/scales.js";

/** The three curves of the committed Figure 2, with the colours it uses. */
const SERIES = [
  { key: "brain-brain", label: "Brain to brain", color: "var(--ink)" },
  { key: "vnc-vnc", label: "Nerve cord to nerve cord", color: "var(--null)" },
  { key: "cross", label: "Across the neck", color: "var(--wire)" },
];

const DOMAIN = [10 ** -4.6, 10 ** -1.5];

export default function DistanceCurves({ data }) {
  const [hover, setHover] = useState(null);
  const curves = SERIES.map((series) => {
    const curve = data.distance.curves[series.key];
    const points = curve.distance_um
      .map((distance, i) => [distance, curve.probability[i]])
      .filter(([, p]) => p >= DOMAIN[0]);
    return { ...series, points };
  });

  return (
    <ChartFrame
      height={400}
      margin={{ top: 34, right: 168, bottom: 50, left: 58 }}
      role="group"
      label="Connection probability against distance, on a logarithmic scale, for brain pairs, nerve-cord pairs and pairs across the neck."
      onPointer={(px, _py, inner) => {
        const x = linear([0, 1000], [0, inner.width]);
        setHover(Math.max(0, Math.min(1000, x.invert(px))));
      }}
      onLeave={() => setHover(null)}
      overlay={({ width, margin }) => {
        if (hover == null) return null;
        const inner = width - margin.left - margin.right;
        const x = linear([0, 1000], [0, inner]);
        const readings = curves
          .map((curve) => {
            const i = nearestIndex(
              curve.points.map(([d]) => d),
              hover,
            );
            return { ...curve, point: curve.points[i] };
          })
          .filter((curve) => curve.point && Math.abs(curve.point[0] - hover) < 30);
        if (!readings.length) return null;
        return (
          <Tooltip x={margin.left + x(readings[0].point[0])} y={margin.top} width={width}>
            <div className="tip-title">{micron(readings[0].point[0])} apart</div>
            {readings.map((curve) => (
              <Row
                key={curve.key}
                label={curve.label}
                value={curve.point[1].toExponential(1).replace("e-", " × 10⁻")}
                color={curve.color}
              />
            ))}
          </Tooltip>
        );
      }}
    >
      {({ width, height }) => {
        const x = linear([0, 1000], [0, width]);
        const y = log(DOMAIN, [height, 0]);
        const labels = spreadLabels(
          curves.map((curve) => ({
            key: curve.key,
            label: curve.label,
            color: curve.color,
            y: y(curve.points[curve.points.length - 1][1]),
          })),
          17,
          0,
          height,
        );
        return (
          <g>
            <YAxis
              scale={y}
              ticks={logTicks(DOMAIN)}
              width={width}
              format={(t) => t.toFixed(Math.max(0, -Math.log10(t)))}
              title="Share of pairs joined by a connection"
            />
            <XAxis
              scale={x}
              ticks={[0, 200, 400, 600, 800, 1000]}
              height={height}
              width={width}
              format={(t) => (t === 1000 ? "1000 µm" : String(t))}
              title="Distance between the two cell types"
            />
            {hover != null && (
              <line x1={x(hover)} x2={x(hover)} y1={0} y2={height} stroke="var(--rule-strong)" strokeWidth="1" />
            )}
            {curves.map((curve) => (
              <path
                key={curve.key}
                d={line(curve.points.map(([d, p]) => [x(d), y(p)]))}
                fill="none"
                stroke={curve.color}
                strokeWidth="2"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            ))}
            {labels.map((item) => (
              <text key={item.key} className="direct-label" x={width + 10} y={item.y} dy="0.32em" fill={item.color}>
                {item.label}
              </text>
            ))}
          </g>
        );
      }}
    </ChartFrame>
  );
}

const LENGTH_ROWS = [
  ["All pairs", "all"],
  ["Brain to brain", "brain-brain"],
  ["Nerve cord to nerve cord", "vnc-vnc"],
  ["Across the neck", "cross"],
];

export function DistanceTable({ data }) {
  return (
    <div className="table-wrap">
      <table className="data">
        <caption>
          Length constant of the fall in connection probability over the first 600 µm, fitted per group of pairs.
        </caption>
        <thead>
          <tr>
            <th scope="col">Pairs</th>
            <th scope="col" className="num-col">
              Length constant
            </th>
            <th scope="col" className="num-col">
              Spearman ρ
            </th>
          </tr>
        </thead>
        <tbody>
          {LENGTH_ROWS.map(([label, key]) => (
            <tr key={key}>
              <th scope="row">{label}</th>
              <td className="num-col">{micron(data.distance.summary[key].length_constant_um)}</td>
              <td className="num-col">{fixed(data.distance.summary[key].spearman_rho, 3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
