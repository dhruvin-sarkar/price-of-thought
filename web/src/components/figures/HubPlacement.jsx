import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, YAxis, barPath } from "../Chart.jsx";
import { useRovingRows } from "./useRovingRows.js";
import { TableWrap } from "../ui.jsx";
import { count, fixed, micron, percent, pValue, sentence, signed } from "../../lib/format.js";
import { useMedia } from "../../lib/hooks.js";
import { line, linear } from "../../lib/scales.js";

/** The three scopes the analysis reports apart, because the brain and the nerve cord lean opposite ways. */
export const SCOPES = [
  { key: "all", label: "All cell types", color: "var(--wire)" },
  { key: "brain", label: "Brain", color: "var(--ink)" },
  { key: "nerve cord", label: "Nerve cord", color: "var(--null)" },
];

const CENTRE_DOMAIN = [0, 340];
const PARTNER_DOMAIN = [0, 500];
const ROW = 62;

export default function HubPlacement({ data }) {
  return (
    <div className="panels is-two">
      <FromCentre data={data} />
      <ToPartners data={data} />
    </div>
  );
}

/** The null: median distance from the centre of a compartment against how well connected a type is. */
function FromCentre({ data }) {
  const [hover, setHover] = useState(null);
  const wide = useMedia("(min-width: 700px)");
  const margin = { top: 34, right: 16, bottom: 48, left: 50 };
  const bins = data.hubs.degree_bins;
  const curves = SCOPES.map((scope) => ({
    ...scope,
    points: bins.filter((bin) => bin.scope === scope.key),
  }));
  const steps = curves[0].points.length;
  const rowProps = useRovingRows(
    curves[0].points.map((bin) => bin.bin),
    setHover,
  );

  return (
    <div>
      <p className="legend">
        {curves.map((curve) => (
          <span key={curve.key}>
            <span className="swatch is-line" style={{ background: curve.color }} aria-hidden="true" />
            {curve.label}
          </span>
        ))}
      </p>
      <ChartFrame
        height={300}
        margin={margin}
        role="group"
        label="Median distance from the centre of the compartment against ten degree deciles, for all cell types and for the brain and the nerve cord apart."
        onPointer={(px, _py, inner) => {
          const x = linear([1, steps], [0, inner.width]);
          setHover(Math.min(steps, Math.max(1, Math.round(x.invert(px)))));
        }}
        onLeave={() => setHover(null)}
        overlay={({ width, margin: m }) => {
          if (hover == null) return null;
          const x = linear([1, steps], [0, width - m.left - m.right]);
          return (
            <Tooltip x={m.left + x(hover)} y={m.top} width={width}>
              <div className="tip-title">Degree decile {hover}</div>
              {curves.map((curve) => {
                const bin = curve.points[hover - 1];
                return (
                  <Row
                    key={curve.key}
                    label={`${curve.label}, degree ${count(bin.median_value)}`}
                    value={micron(bin.median_distance_um)}
                    color={curve.color}
                  />
                );
              })}
            </Tooltip>
          );
        }}
      >
        {({ width, height }) => {
          const x = linear([1, steps], [0, width]);
          const y = linear(CENTRE_DOMAIN, [height, 0]);
          const band = width / steps;
          return (
            <g>
              <YAxis
                scale={y}
                ticks={[0, 100, 200, 300]}
                width={width}
                format={String}
                title="Median distance from the centre (µm)"
                inset={margin.left - 4}
              />
              <XAxis
                scale={x}
                ticks={wide ? curves[0].points.map((bin) => bin.bin) : [1, 5, 10]}
                height={height}
                width={width}
                margin={margin}
                format={String}
                title="Degree decile, least connected first"
              />
              {curves.map((curve) => (
                <path
                  key={curve.key}
                  data-mark="line"
                  pathLength="1"
                  d={line(curve.points.map((bin) => [x(bin.bin), y(bin.median_distance_um)]))}
                  fill="none"
                  stroke={curve.color}
                  strokeWidth="2"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              ))}
              {curves[0].points.map((bin) => (
                <g
                  key={bin.bin}
                  {...rowProps(bin.bin)}
                  role="img"
                  aria-label={`Degree decile ${bin.bin}: ${curves
                    .map(
                      (curve) =>
                        `${curve.label} ${micron(curve.points[bin.bin - 1].median_distance_um)} at a median degree ` +
                        `of ${count(curve.points[bin.bin - 1].median_value)}`,
                    )
                    .join(", ")}`}
                >
                  <rect
                    className="row-band"
                    x={Math.min(Math.max(x(bin.bin) - band / 2, 0), width - band)}
                    width={band}
                    y={-2}
                    height={height + 4}
                    rx={3}
                  />
                  {curves.map((curve) => (
                    <circle
                      key={curve.key}
                      cx={x(bin.bin)}
                      cy={y(curve.points[bin.bin - 1].median_distance_um)}
                      r={hover === bin.bin ? 4.5 : 3}
                      fill={curve.color}
                    />
                  ))}
                </g>
              ))}
            </g>
          );
        }}
      </ChartFrame>
    </div>
  );
}

/** The positive: how far a type sits from its own partners, against partners drawn to match its degree. */
function ToPartners({ data }) {
  const [hover, setHover] = useState(null);
  const margin = { top: 34, right: 20, bottom: 48, left: 12 };
  const partners = data.hubs.partners;
  const rows = SCOPES.map((scope) => ({ ...scope, result: partners.scopes[scope.key] }));
  const height = margin.top + margin.bottom + rows.length * ROW;
  const rowProps = useRovingRows(
    rows.map((row) => row.key),
    (key) => setHover(key == null ? null : rows.findIndex((row) => row.key === key)),
  );

  return (
    <div>
      <p className="legend">
        <span>
          <span className="swatch" style={{ background: "var(--wire)" }} aria-hidden="true" />
          Its own partners
        </span>
        <span>
          <span className="swatch" style={{ background: "var(--ink-3)" }} aria-hidden="true" />
          Degree-matched random partners
        </span>
      </p>
      <ChartFrame
        height={height}
        margin={margin}
        role="group"
        label="Mean distance from a cell type to the centroid of its own partners against degree-matched random partners, for all cell types and for the brain and the nerve cord apart."
        onPointer={(_x, y, inner) => {
          const index = Math.floor(y / (inner.height / rows.length));
          setHover(index >= 0 && index < rows.length ? index : null);
        }}
        onLeave={() => setHover(null)}
        overlay={({ height: inner, margin: m, width }) => {
          if (hover == null) return null;
          const row = rows[hover];
          const step = inner / rows.length;
          const x = linear(PARTNER_DOMAIN, [0, width - m.left - m.right]);
          return (
            <Tooltip x={m.left + x(row.result.null_mean_um)} y={m.top + hover * step + 14} width={width}>
              <div className="tip-title">{sentence(row.label)}</div>
              <Row label="Its own partners" value={micron(row.result.real_um, 1)} />
              <Row
                label="Random partners"
                value={`${micron(row.result.null_mean_um, 1)} ± ${fixed(row.result.null_sd_um, 2)}`}
              />
              <Row label="Ratio" value={fixed(row.result.ratio, 3)} />
              <Row label="z" value={fixed(row.result.z_score, 1)} />
              <Row
                label="At or below real"
                value={`${count(row.result.n_at_or_below_real)} of ${count(row.result.permutations)}`}
              />
            </Tooltip>
          );
        }}
      >
        {({ width, height: inner }) => {
          const x = linear(PARTNER_DOMAIN, [0, width]);
          const step = inner / rows.length;
          return (
            <g>
              <XAxis
                scale={x}
                ticks={[0, 100, 200, 300, 400, 500]}
                height={inner}
                width={width}
                margin={margin}
                format={String}
                title="Distance to the centroid of the partners (µm)"
              />
              {rows.map((row, i) => {
                const top = i * step;
                return (
                  <g
                    key={row.key}
                    {...rowProps(row.key)}
                    role="img"
                    aria-label={`${row.label}: ${micron(row.result.real_um, 1)} to its own partners against ${micron(
                      row.result.null_mean_um,
                      1,
                    )} for degree-matched random partners, a ratio of ${fixed(row.result.ratio, 3)}, z ${fixed(
                      row.result.z_score,
                      1,
                    )}`}
                  >
                    <rect
                      className="row-band"
                      x={-margin.left + 2}
                      width={width + margin.left + margin.right - 4}
                      y={top + 1}
                      height={step - 2}
                      rx={3}
                    />
                    <text className="row-label" x={0} y={top + 14}>
                      {row.label}
                    </text>
                    <path
                      data-mark="bar"
                      d={barPath(0, top + 22, x(row.result.real_um), 13)}
                      fill="var(--wire)"
                      opacity={hover === i ? 1 : 0.9}
                    />
                    <path
                      data-mark="bar"
                      d={barPath(0, top + 38, x(row.result.null_mean_um), 13)}
                      fill="var(--ink-3)"
                      opacity={hover === i ? 1 : 0.9}
                    />
                    <text className="mark-label" x={x(row.result.real_um) + 7} y={top + 33}>
                      {fixed(row.result.real_um, 0)}
                    </text>
                    <text className="mark-label" x={x(row.result.null_mean_um) + 7} y={top + 49}>
                      {fixed(row.result.null_mean_um, 0)}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        }}
      </ChartFrame>
    </div>
  );
}

const MEASURES = { degree: "degree", wire: "wire" };

/** The values behind the figure: the correlations that find nothing, and the partner test that does. */
export function HubPlacementTable({ data }) {
  const { scopes, correlations, partners, totals } = data.hubs;
  const byScope = Object.fromEntries(scopes.map((scope) => [scope.scope, scope]));
  return (
    <>
      <TableWrap label="Values behind Figure 16: degree and wire against distance from the centre">
        <table className="data">
          <caption>
            Distance is measured from the centroid of the cell types of that scope, not of the whole specimen: the
            brain and the nerve cord occupy different volumes, and a shared centre would rank a type by which
            compartment it belongs to rather than by where it sits inside it. `wire` is the summed length of the
            connections a type takes part in. Pearson&rsquo;s r is taken on the base-ten logarithm of the measure,
            over the types with a positive value; {count(totals.isolated_types)} of the {count(totals.types)} types
            have no connection at all.
          </caption>
          <thead>
            <tr>
              <th scope="col">Scope</th>
              <th scope="col">Measure</th>
              <th scope="col" className="num-col">
                Types
              </th>
              <th scope="col" className="num-col">
                Median distance
              </th>
              <th scope="col" className="num-col">
                ρ
              </th>
              <th scope="col" className="num-col">
                p
              </th>
              <th scope="col" className="num-col">
                Pearson r on logs
              </th>
            </tr>
          </thead>
          <tbody>
            {correlations.map((row) => (
              <tr key={`${row.scope}-${row.measure}`}>
                <th scope="row">{sentence(row.scope)}</th>
                <td>{MEASURES[row.measure] ?? row.measure}</td>
                <td className="num-col">{count(row.types)}</td>
                <td className="num-col">{micron(byScope[row.scope].median_distance_um, 1)}</td>
                <td className="num-col">{signed(row.spearman_rho, 3)}</td>
                <td className="num-col">{pValue(row.spearman_p)}</td>
                <td className="num-col">{signed(row.pearson_log_r, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>

      <TableWrap label="Values behind Figure 16: distance to a type's own partners against a degree-matched redraw">
        <table className="data">
          <caption>
            Each type keeps its degree and draws that many partners uniformly at random from the other types, never
            itself, with replacement; {count(partners.scopes.all.permutations)} draws, seeded from {partners.seed}.{" "}
            {count(partners.types_tested)} of the {count(totals.types)} types have at least one connection and are
            tested, and {percent(partners.share_nearer_than_chance)} of them sit nearer their own partners than
            their own null mean.
          </caption>
          <thead>
            <tr>
              <th scope="col">Scope</th>
              <th scope="col" className="num-col">
                Its own partners
              </th>
              <th scope="col" className="num-col">
                Random partners
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
              <th scope="col" className="num-col">
                p
              </th>
            </tr>
          </thead>
          <tbody>
            {SCOPES.map((scope) => {
              const result = partners.scopes[scope.key];
              return (
                <tr key={scope.key}>
                  <th scope="row">{sentence(scope.key)}</th>
                  <td className="num-col">{micron(result.real_um, 1)}</td>
                  <td className="num-col">
                    {micron(result.null_mean_um, 1)} ± {fixed(result.null_sd_um, 2)}
                  </td>
                  <td className="num-col">{fixed(result.ratio, 3)}</td>
                  <td className="num-col">{fixed(result.z_score, 1)}</td>
                  <td className="num-col">
                    {count(result.n_at_or_below_real)} / {count(result.permutations)}
                  </td>
                  <td className="num-col">{pValue(result.p_value)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </TableWrap>

      <TableWrap label="Values behind Figure 16: the cell types furthest below their own null">
        <table className="data">
          <caption>
            The {partners.extremes.length} cell types sitting furthest below their own null, in units of that
            null&rsquo;s standard deviation.
          </caption>
          <thead>
            <tr>
              <th scope="col">Cell type</th>
              <th scope="col">Side</th>
              <th scope="col">Compartment</th>
              <th scope="col" className="num-col">
                Degree
              </th>
              <th scope="col" className="num-col">
                Distance to its partners
              </th>
              <th scope="col" className="num-col">
                z
              </th>
            </tr>
          </thead>
          <tbody>
            {partners.extremes.map((row) => (
              <tr key={`${row.cell_type}-${row.side}`}>
                <th scope="row">{row.cell_type}</th>
                <td>{row.side}</td>
                <td>{row.compartment === "vnc" ? "nerve cord" : "brain"}</td>
                <td className="num-col">{count(row.degree)}</td>
                <td className="num-col">{micron(row.distance_to_partners_um, 1)}</td>
                <td className="num-col">{fixed(row.z_score, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
    </>
  );
}
