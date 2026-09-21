import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, barPath } from "../Chart.jsx";
import { useRovingRows } from "./useRovingRows.js";
import { TableWrap } from "../ui.jsx";
import { count, fixed, pValue, percent, times } from "../../lib/format.js";
import { linear } from "../../lib/scales.js";

const ROW = 34;
// Wide enough to hold every band end and every ratio, so nothing has to be cut short to fit.
const DOMAIN = [0.7, 1.65];
const clamp = (v) => Math.min(Math.max(v, DOMAIN[0]), DOMAIN[1]);

/** The rewired 95% band, as a ratio to the rewired mean, the way the results files report it. */
const band = (result) => {
  const spread = (1.96 * result.null_sd) / result.null_mean;
  return [1 - spread, 1 + spread];
};

function RatioRows({ rows, title, label }) {
  const [hover, setHover] = useState(null);
  const margin = { top: 30, right: 54, bottom: 46, left: 76 };
  const height = margin.top + margin.bottom + rows.length * ROW;
  const rowProps = useRovingRows(
    rows.map((row) => row.key),
    (key) => setHover(key == null ? null : rows.findIndex((row) => row.key === key)),
  );

  return (
    <ChartFrame
      height={height}
      margin={margin}
      role="group"
      label={label}
      onPointer={(_x, y, inner) => {
        const index = Math.floor(y / (inner.height / rows.length));
        setHover(index >= 0 && index < rows.length ? index : null);
      }}
      onLeave={() => setHover(null)}
      overlay={({ height: inner, margin: m, width }) => {
        if (hover == null) return null;
        const row = rows[hover];
        const step = inner / rows.length;
        const x = linear(DOMAIN, [0, width - m.left - m.right]);
        return (
          <Tooltip x={m.left + x(clamp(row.ratio))} y={m.top + hover * step + step / 2 - 4} width={width}>
            <div className="tip-title">{row.title}</div>
            <Row label="Real routes" value={count(row.real)} />
            <Row label="Rewired mean" value={count(row.nullMean)} />
            <Row label="Ratio" value={times(row.ratio, 3)} />
            <Row label="p" value={pValue(row.p)} />
          </Tooltip>
        );
      }}
    >
      {({ width, height: inner }) => {
        const x = linear(DOMAIN, [0, width]);
        const step = inner / rows.length;
        return (
          <g>
            <text className="axis-title" x={-margin.left + 4} y={-14}>
              {title}
            </text>
            <XAxis
              scale={x}
              ticks={[0.8, 1, 1.2, 1.4, 1.6]}
              height={inner}
              width={width}
              format={(t) => t.toFixed(1)}
              title="Real routes / rewired mean"
            />
            <line x1={x(1)} x2={x(1)} y1={-6} y2={inner} stroke="var(--rule-strong)" strokeDasharray="3 3" />
            {rows.map((row, i) => {
              const y = i * step + step / 2;
              const [lo, hi] = row.band;
              return (
                <g
                  key={row.key}
                  {...rowProps(row.key)}
                  role="img"
                  aria-label={`${row.title}: ${fixed(row.ratio, 3)} times the rewired mean, ${count(
                    row.real,
                  )} real routes against ${count(row.nullMean)}, p ${pValue(row.p)}`}
                >
                  <rect
                    className="row-band"
                    x={-margin.left + 2}
                    width={width + margin.left + margin.right - 4}
                    y={i * step + 1}
                    height={step - 2}
                    rx={3}
                  />
                  {/* The band the rewirings occupy; a point outside it is the result. */}
                  <path data-mark="bar" d={barPath(x(clamp(lo)), y - 5, x(clamp(hi)) - x(clamp(lo)), 10, 2)} fill="var(--wash)" />
                  <text className="row-label" x={-12} y={y} dy="0.32em" textAnchor="end">
                    {row.label}
                  </text>
                  <circle
                    data-mark="fade"
                    cx={x(clamp(row.ratio))}
                    cy={y}
                    r="5.5"
                    fill={row.significant ? "var(--wire)" : "var(--paper)"}
                    stroke={row.significant ? "var(--wire)" : "var(--ink-3)"}
                    strokeWidth="2"
                  />
                  <text className="mark-label" x={width + 8} y={y} dy="0.32em">
                    {fixed(row.ratio, 3)}
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

export default function RichClub({ data }) {
  const byRichness = data.richclub.threshold_curve.map((row) => ({
    key: `rich-${row.top_fraction}`,
    label: percent(row.top_fraction, 0),
    title: `Top ${percent(row.top_fraction, 0)} of partners counted as rich`,
    ratio: row.ratio,
    real: row.real,
    nullMean: row.null_mean,
    p: row.p_value,
    significant: row.p_value <= 0.05,
    band: [row.ratio_lo, row.ratio_hi],
  }));

  const byThreshold = (data.robustness?.thresholds ?? []).map((row) => ({
    key: `edge-${row.fraction}`,
    label: percent(row.fraction, 1),
    title: `Connections at ${percent(row.fraction, 1)} of a target's input`,
    ratio: row.routes.total.ratio,
    real: row.routes.total.real,
    nullMean: row.routes.total.null_mean,
    p: row.routes.total.p_value,
    significant: row.routes.total.significant,
    band: band(row.routes.total),
  }));

  return (
    <div className="panels">
      <RatioRows
        rows={byRichness}
        title="By the share of partners counted as rich"
        label="Ratio of real rich-to-rich routes through the connective to the rewired mean, at seven definitions of a rich partner."
      />
      <RatioRows
        rows={byThreshold}
        title="By the edge threshold of the whole graph"
        label="Ratio of real rich-to-rich routes to the rewired mean at four edge thresholds."
      />
    </div>
  );
}

export function RichClubTable({ data }) {
  const routes = data.richclub.routes;
  const directions = [
    ["all (primary)", routes.total],
    ["descending, brain to cord", routes.descending],
    ["ascending, cord to brain", routes.ascending],
  ];
  return (
    <>
      <TableWrap label="Values behind Figure 8: rich-to-rich routes by direction">
        <table className="data">
          <caption>Routes counted with the top 10% of partners on each side treated as rich.</caption>
          <thead>
            <tr>
              <th scope="col">Routes</th>
              <th scope="col" className="num-col">
                Real
              </th>
              <th scope="col" className="num-col">
                Rewired mean ± SD
              </th>
              <th scope="col" className="num-col">
                Ratio
              </th>
              <th scope="col" className="num-col">
                p
              </th>
            </tr>
          </thead>
          <tbody>
            {directions.map(([label, result]) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                <td className="num-col">{count(result.real)}</td>
                <td className="num-col">
                  {count(result.null_mean)} ± {count(result.null_sd)}
                </td>
                <td className="num-col">{fixed(result.ratio, 3)}</td>
                <td className="num-col">{pValue(result.p_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      {data.robustness && (
        <TableWrap label="Values behind Figure 8: the same tests at four edge thresholds">
          <table className="data">
            <caption>The same tests at four edge thresholds.</caption>
            <thead>
              <tr>
                <th scope="col">Edge threshold</th>
                <th scope="col" className="num-col">
                  Connections
                </th>
                <th scope="col" className="num-col">
                  Route ratio
                </th>
                <th scope="col" className="num-col">
                  p
                </th>
                <th scope="col" className="num-col">
                  Hub odds ratio
                </th>
                <th scope="col" className="num-col">
                  Placement ratio
                </th>
              </tr>
            </thead>
            <tbody>
              {data.robustness.thresholds.map((row) => (
                <tr key={row.fraction}>
                  <th scope="row">{percent(row.fraction, 1)}</th>
                  <td className="num-col">{count(row.edges)}</td>
                  <td className="num-col">{fixed(row.routes.total.ratio, 3)}</td>
                  <td className="num-col">{pValue(row.routes.total.p_value)}</td>
                  <td className="num-col">{fixed(row.hubs.odds_ratio, 2)}</td>
                  <td className="num-col">{fixed(row.placement.cost_ratio, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      )}
      <p className="caption">
        p = (1 + k) / 1001, where k is the number of rewirings with at least as many routes; 0.001 is the smallest
        attainable.
      </p>
    </>
  );
}
