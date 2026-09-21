import { useMemo, useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, YAxis } from "../Chart.jsx";
import { TableWrap } from "../ui.jsx";
import { count, fixed, micron, pValue, superclassName } from "../../lib/format.js";
import { log, logTicks } from "../../lib/scales.js";

const ORDER = ["descending_neuron", "ascending_neuron", "cb_intrinsic", "vnc_intrinsic"];
const CONNECTIVE = new Set(["descending_neuron", "ascending_neuron"]);

function Panel({ superclass, points, test, domainX, domainY }) {
  const [hover, setHover] = useState(null);
  const color = CONNECTIVE.has(superclass) ? "var(--wire)" : "var(--ink-3)";

  return (
    <ChartFrame
      height={230}
      margin={{ top: 44, right: 16, bottom: 46, left: 52 }}
      role="group"
      label={`${superclassName(superclass)} neurons: skeleton cable length against soma-to-output distance, Spearman rho ${test.spearman_rho.toFixed(3)}.`}
      onPointer={(px, py, inner) => {
        const x = log(domainX, [0, inner.width]);
        const y = log(domainY, [inner.height, 0]);
        let best = null;
        let distance = 16 * 16;
        points.forEach((point, index) => {
          const dx = x(point.soma_to_output_um) - px;
          const dy = y(point.cable_um) - py;
          const d = dx * dx + dy * dy;
          if (d < distance) {
            distance = d;
            best = { ...point, index };
          }
        });
        setHover(best);
      }}
      onLeave={() => setHover(null)}
      overlay={({ width, height, margin }) => {
        if (!hover) return null;
        const x = log(domainX, [0, width - margin.left - margin.right]);
        const y = log(domainY, [height, 0]);
        return (
          <Tooltip x={margin.left + x(hover.soma_to_output_um)} y={margin.top + y(hover.cable_um) - 6} width={width}>
            <div className="tip-title">{superclassName(superclass)} neuron</div>
            <Row label="Soma to output" value={micron(hover.soma_to_output_um)} />
            <Row label="Skeleton cable" value={micron(hover.cable_um)} />
          </Tooltip>
        );
      }}
    >
      {({ width, height }) => {
        const x = log(domainX, [0, width]);
        const y = log(domainY, [height, 0]);
        return (
          <g>
            <text className="axis-title" x={-44} y={-26}>
              {superclassName(superclass)}
            </text>
            <text className="mark-label" x={-44} y={-10}>
              ρ = {fixed(test.spearman_rho, 3)}, {count(test.n)} neurons
            </text>
            <YAxis
              scale={y}
              ticks={logTicks(domainY)}
              width={width}
              format={(t) => (t >= 1000 ? `${t / 1000}k` : String(t))}
            />
            <XAxis
              scale={x}
              ticks={logTicks(domainX)}
              height={height}
              width={width}
              format={(t) => (t >= 1000 ? `${t / 1000}k` : String(t))}
              title="Soma to output (µm)"
            />
            <g data-mark="fade">
              {points.map((point, index) => (
                <circle
                  key={`${point.soma_to_output_um}-${point.cable_um}-${index}`}
                  cx={x(point.soma_to_output_um)}
                  cy={y(point.cable_um)}
                  r={hover?.index === index ? 5 : 3}
                  fill={color}
                  fillOpacity={hover?.index === index ? 1 : 0.45}
                />
              ))}
            </g>
          </g>
        );
      }}
    </ChartFrame>
  );
}

export default function CableLength({ data }) {
  const grouped = useMemo(() => {
    const groups = Object.fromEntries(ORDER.map((key) => [key, []]));
    for (const point of data.cable.points) groups[point.superclass]?.push(point);
    return groups;
  }, [data]);

  const positive = data.cable.points.filter((p) => p.soma_to_output_um > 0 && p.cable_um > 0);
  const domainX = [
    Math.min(...positive.map((p) => p.soma_to_output_um)) * 0.8,
    Math.max(...positive.map((p) => p.soma_to_output_um)) * 1.25,
  ];
  const domainY = [
    Math.min(...positive.map((p) => p.cable_um)) * 0.8,
    Math.max(...positive.map((p) => p.cable_um)) * 1.25,
  ];

  return (
    <div className="panels is-four">
      {ORDER.map((superclass) => (
        <Panel
          key={superclass}
          superclass={superclass}
          points={grouped[superclass]}
          test={data.cable.by_superclass[superclass]}
          domainX={domainX}
          domainY={domainY}
        />
      ))}
    </div>
  );
}

export function CableTable({ data }) {
  return (
    <TableWrap label="Values behind Figure 19: cable length against soma-to-output distance by class">
      <table className="data">
        <caption>
          Skeleton cable length against soma-to-output distance for {count(data.cable.analysed)} sampled neurons.
          Pooled across classes ρ = {fixed(data.cable.spearman_rho, 3)} ({pValue(data.cable.p_value)}); within each
          class it is near zero, so positions capture differences between classes, not the cable of individual
          neurons.
        </caption>
        <thead>
          <tr>
            <th scope="col">Class</th>
            <th scope="col" className="num-col">
              Neurons
            </th>
            <th scope="col" className="num-col">
              ρ
            </th>
            <th scope="col" className="num-col">
              p
            </th>
            <th scope="col" className="num-col">
              Median cable
            </th>
            <th scope="col" className="num-col">
              Median soma to output
            </th>
          </tr>
        </thead>
        <tbody>
          {ORDER.map((superclass) => {
            const test = data.cable.by_superclass[superclass];
            return (
              <tr key={superclass}>
                <th scope="row">{superclassName(superclass)}</th>
                <td className="num-col">{count(test.n)}</td>
                <td className="num-col">{fixed(test.spearman_rho, 3)}</td>
                <td className="num-col">{pValue(test.p_value)}</td>
                <td className="num-col">{micron(test.median_cable_um)}</td>
                <td className="num-col">{micron(test.median_soma_to_output_um)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </TableWrap>
  );
}
