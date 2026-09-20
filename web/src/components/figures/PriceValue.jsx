import { useMemo, useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, YAxis } from "../Chart.jsx";
import { count, fixed, millimetre, pValue } from "../../lib/format.js";
import { linear, log, logTicks, niceTicks } from "../../lib/scales.js";

const DIRECTIONS = [
  { key: "descending", label: "Descending types, brain to nerve cord" },
  { key: "ascending", label: "Ascending types, nerve cord to brain" },
];

function Panel({ title, points, test }) {
  const [hover, setHover] = useState(null);
  const domain = useMemo(() => {
    const prices = points.map((p) => p.price_um).filter((v) => v > 0);
    return [Math.min(...prices) * 0.8, Math.max(...prices) * 1.2];
  }, [points]);
  const valueMax = Math.max(1, ...points.map((p) => p.value));

  return (
    <ChartFrame
      height={330}
      margin={{ top: 40, right: 22, bottom: 50, left: 48 }}
      role="group"
      label={`${title}: total length of each cell type's neck-crossing wiring against the sensory-to-motor flow lost when that wiring alone is removed.`}
      onPointer={(px, py, inner) => {
        const x = log(domain, [0, inner.width]);
        const y = linear([0, valueMax], [inner.height, 0]);
        let best = null;
        let distance = 18 * 18;
        for (const point of points) {
          if (point.price_um <= 0) continue;
          const dx = x(point.price_um) - px;
          const dy = y(point.value) - py;
          const d = dx * dx + dy * dy;
          if (d < distance) {
            distance = d;
            best = point;
          }
        }
        setHover(best);
      }}
      onLeave={() => setHover(null)}
      overlay={({ width, height, margin }) => {
        if (!hover) return null;
        const x = log(domain, [0, width - margin.left - margin.right]);
        const y = linear([0, valueMax], [height, 0]);
        return (
          <Tooltip x={margin.left + x(hover.price_um)} y={margin.top + y(hover.value) - 6} width={width}>
            <div className="tip-title">
              {hover.cell_type} {hover.side}
            </div>
            <Row label="Neck-crossing wire" value={millimetre(hover.price_um)} />
            <Row label="Connections" value={count(hover.edges)} />
            <Row label="Flow lost when removed" value={count(hover.value)} />
          </Tooltip>
        );
      }}
    >
      {({ width, height }) => {
        const x = log(domain, [0, width]);
        const y = linear([0, valueMax], [height, 0]);
        return (
          <g>
            <text className="axis-title" x={-40} y={-24}>
              {title}
            </text>
            <YAxis
              scale={y}
              ticks={niceTicks([0, valueMax], 4, { integer: true })}
              width={width}
              format={count}
              title="Flow lost when its wiring is removed"
              inset={40}
            />
            <XAxis
              scale={x}
              ticks={logTicks(domain)}
              height={height}
              width={width}
              format={(t) => millimetre(t)}
              title="Total neck-crossing wire"
            />
            {points.map((point) =>
              point.price_um > 0 ? (
                <circle
                  key={point.node}
                  cx={x(point.price_um)}
                  cy={y(point.value)}
                  r={hover?.node === point.node ? 5 : 3}
                  fill={point.value > 0 ? "var(--wire)" : "var(--ink-3)"}
                  fillOpacity={hover?.node === point.node ? 1 : 0.42}
                />
              ) : null,
            )}
            {/* Set beside the panel title rather than in the plot, where the zero row of points already sits. */}
            <text className="mark-label" x={width} y={-24} textAnchor="end">
              {count(test.zero_value)} of {count(test.n)} lose no flow
            </text>
          </g>
        );
      }}
    </ChartFrame>
  );
}

export default function PriceValue({ data }) {
  const byDirection = useMemo(() => {
    const groups = { descending: [], ascending: [] };
    for (const row of data.price.nodes) groups[row.direction]?.push(row);
    return groups;
  }, [data]);

  return (
    <div className="panels is-two">
      {DIRECTIONS.map((direction) => (
        <Panel
          key={direction.key}
          title={direction.label}
          points={byDirection[direction.key]}
          test={data.price.tests[direction.key]}
        />
      ))}
    </div>
  );
}

export function PriceTestsTable({ data }) {
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            <th scope="col">Direction</th>
            <th scope="col" className="num-col">
              Types
            </th>
            <th scope="col" className="num-col">
              Lose no flow
            </th>
            <th scope="col" className="num-col">
              ρ
            </th>
            <th scope="col" className="num-col">
              Partial ρ given connections
            </th>
            <th scope="col" className="num-col">
              p
            </th>
          </tr>
        </thead>
        <tbody>
          {DIRECTIONS.map((direction) => {
            const test = data.price.tests[direction.key];
            return (
              <tr key={direction.key}>
                <th scope="row">{direction.key}</th>
                <td className="num-col">{count(test.n)}</td>
                <td className="num-col">{count(test.zero_value)}</td>
                <td className="num-col">{fixed(test.spearman_rho, 3)}</td>
                <td className="num-col">{fixed(test.partial_rho, 3)}</td>
                <td className="num-col">{pValue(test.partial_p_value)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
