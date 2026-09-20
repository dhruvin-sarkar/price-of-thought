import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, barPath } from "../Chart.jsx";
import { fixed, propertyName, propertyValue } from "../../lib/format.js";
import { log } from "../../lib/scales.js";

const ROW = 30;
const DOMAIN = [0.55, 30];
const TICKS = [1, 2, 5, 10, 20];

/** Each property as a multiple of the synthetic mean, so thirteen different units share one axis. */
function relative(properties) {
  return Object.entries(properties).map(([key, property]) => {
    const mean = property.synthetic_mean || 1;
    return {
      key,
      label: propertyName(key),
      ratio: property.real / mean,
      band: [property.interval_95[0] / mean, property.interval_95[1] / mean],
      property,
    };
  });
}

export default function Generative({ data, model }) {
  const [hover, setHover] = useState(null);
  const rows = relative(data.generative.comparison.models[model].properties);
  const margin = { top: 30, right: 56, bottom: 46, left: 196 };
  const height = margin.top + margin.bottom + rows.length * ROW;

  return (
    <ChartFrame
      height={height}
      margin={margin}
      role="group"
      label={`Thirteen properties of the real graph as a multiple of the mean of ${data.generative.comparison.n_synthetic} synthetic graphs from model ${model}, with the synthetic central 95% range.`}
      onPointer={(_x, y, inner) => {
        const index = Math.floor(y / (inner.height / rows.length));
        setHover(index >= 0 && index < rows.length ? index : null);
      }}
      onLeave={() => setHover(null)}
      overlay={({ height: inner, margin: m, width }) => {
        if (hover == null) return null;
        const row = rows[hover];
        const step = inner / rows.length;
        const x = log(DOMAIN, [0, width - m.left - m.right]);
        return (
          <Tooltip
            x={m.left + x(Math.min(Math.max(row.ratio, DOMAIN[0]), DOMAIN[1]))}
            y={m.top + hover * step + step / 2 - 4}
            width={width}
          >
            <div className="tip-title">{row.label}</div>
            <Row label="Real" value={propertyValue(row.key, row.property.real)} />
            <Row label="Synthetic mean" value={propertyValue(row.key, row.property.synthetic_mean)} />
            <Row
              label="Synthetic 95%"
              value={`${propertyValue(row.key, row.property.interval_95[0])} to ${propertyValue(
                row.key,
                row.property.interval_95[1],
              )}`}
            />
            <Row label="Reproduced" value={row.property.reproduced ? "yes" : "no"} />
          </Tooltip>
        );
      }}
    >
      {({ width, height: inner }) => {
        const x = log(DOMAIN, [0, width]);
        const step = inner / rows.length;
        return (
          <g>
            <XAxis
              scale={x}
              ticks={TICKS}
              height={inner}
              width={width}
              format={(t) => `${t}×`}
              title="Real value / synthetic mean"
            />
            <line x1={x(1)} x2={x(1)} y1={-6} y2={inner} stroke="var(--rule-strong)" strokeDasharray="3 3" />
            {rows.map((row, i) => {
              const y = i * step + step / 2;
              const lo = Math.max(DOMAIN[0], row.band[0]);
              const hi = Math.min(DOMAIN[1], row.band[1]);
              const at = Math.min(Math.max(row.ratio, DOMAIN[0]), DOMAIN[1]);
              return (
                <g key={row.key}>
                  <text className="row-label" x={-12} y={y} dy="0.32em" textAnchor="end">
                    {row.label}
                  </text>
                  <path d={barPath(x(lo), y - 4.5, Math.max(3, x(hi) - x(lo)), 9, 2)} fill="var(--wash)" />
                  <circle
                    cx={x(at)}
                    cy={y}
                    r="5"
                    fill={row.property.reproduced ? "var(--paper)" : "var(--wire)"}
                    stroke={row.property.reproduced ? "var(--ink-2)" : "var(--wire)"}
                    strokeWidth="2"
                  />
                  <text className="mark-label" x={width + 8} y={y} dy="0.32em">
                    {fixed(row.ratio, row.ratio >= 10 ? 1 : 2)}
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

export function GenerativeTable({ data, model }) {
  const properties = data.generative.comparison.models[model].properties;
  return (
    <div className="table-wrap">
      <table className="data">
        <caption>
          A property counts as reproduced when the real value falls inside the central 95% of the{" "}
          {data.generative.comparison.n_synthetic} synthetic graphs.
        </caption>
        <thead>
          <tr>
            <th scope="col">Property</th>
            <th scope="col" className="num-col">
              Real
            </th>
            <th scope="col" className="num-col">
              Synthetic mean
            </th>
            <th scope="col" className="num-col">
              Synthetic central 95%
            </th>
            <th scope="col">Reproduced</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(properties).map(([key, property]) => (
            <tr key={key}>
              <th scope="row">{propertyName(key)}</th>
              <td className="num-col">{propertyValue(key, property.real)}</td>
              <td className="num-col">{propertyValue(key, property.synthetic_mean)}</td>
              <td className="num-col">
                {propertyValue(key, property.interval_95[0])} to {propertyValue(key, property.interval_95[1])}
              </td>
              <td>{property.reproduced ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const FITS = [
  ["distance only", "distance"],
  ["distance and compartment", "distance_compartment"],
  ["model G: distance, compartment and cell class", "G"],
  ["model G+deg, adding degrees", "G_deg"],
];

export function FitTable({ data }) {
  return (
    <div className="table-wrap">
      <table className="data">
        <caption>Logistic fits of edge presence, with five-fold cross-validated AUC.</caption>
        <thead>
          <tr>
            <th scope="col">Model</th>
            <th scope="col" className="num-col">
              Pseudo-R²
            </th>
            <th scope="col" className="num-col">
              Cross-validated AUC
            </th>
            <th scope="col" className="num-col">
              Parameters
            </th>
          </tr>
        </thead>
        <tbody>
          {FITS.map(([label, key]) => {
            const fit = data.generative.fit.models[key];
            return (
              <tr key={key}>
                <th scope="row">{label}</th>
                <td className="num-col">{fixed(fit.pseudo_r2_mcfadden, 3)}</td>
                <td className="num-col">{fixed(fit.cv_auc_mean, 3)}</td>
                <td className="num-col">{fit.parameters}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
