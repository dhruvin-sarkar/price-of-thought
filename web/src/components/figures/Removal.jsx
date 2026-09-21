import { useState } from "react";
import { ChartFrame, Row, Tooltip, XAxis, YAxis } from "../Chart.jsx";
import { useRovingRows } from "./useRovingRows.js";
import { TableWrap } from "../ui.jsx";
import { count, fixed, percent } from "../../lib/format.js";
import { useMedia } from "../../lib/hooks.js";
import { line, linear } from "../../lib/scales.js";

/** The three removal schedules, in the order the result file reports them. */
export const SCHEDULES = [
  { key: "longest first", label: "Longest first", color: "var(--wire)" },
  { key: "shortest first", label: "Shortest first", color: "var(--ink)" },
  { key: "random, matched count", label: "At random", color: "var(--null)" },
];

/** The two ways the schedules are matched to each other: on the wire they remove, or on the count. */
export const AXES = [
  { value: "wire", label: "Wire removed" },
  { value: "edges", label: "Connections removed" },
];

const AXIS = {
  wire: {
    field: "wire_removed_share",
    domain: [0, 0.6],
    ticks: [0, 0.15, 0.3, 0.45, 0.6],
    title: "Share of the wiring budget removed",
    noun: "of the wire",
  },
  edges: {
    field: "edges_removed_share",
    domain: [0, 0.85],
    ticks: [0, 0.2, 0.4, 0.6, 0.8],
    title: "Share of the connections removed",
    noun: "of the connections",
  },
};

const SHARES = [0, 0.25, 0.5, 0.75, 1];
const COMPONENT_SHARES = [0.75, 0.8, 0.85, 0.9, 0.95, 1];

const metres = (um) => `${fixed(um / 1e6, 2)} m`;

/**
 * Three curves read against the same eighteen sample points. One tab stop walks the points; at each one the
 * readout gives every schedule its own position on the axis, because only two of the three share it.
 */
function Curves({ data, axis, field, domain, ticks = SHARES, title, label, describe, mark }) {
  const [hover, setHover] = useState(null);
  const view = AXIS[axis];
  // Narrow enough and the axis title and the reference label no longer fit on one line, so they stack.
  const wide = useMedia("(min-width: 700px)");
  const margin = { top: wide ? 34 : 48, right: 26, bottom: 52, left: 52 };
  const curves = SCHEDULES.map((schedule) => ({
    ...schedule,
    points: data.tradeoff.curves[schedule.key],
  }));
  const steps = curves[0].points.length;
  const indices = curves[0].points.map((_, i) => i);
  const rowProps = useRovingRows(indices, setHover);
  const at = data.tradeoff.comparison.at_reference["longest first"][view.field];
  const inside = (point) => point[view.field] <= view.domain[1] + 1e-9;

  return (
    <>
      <p className="legend">
        {curves.map((curve) => (
          <span key={curve.key}>
            <span className="swatch is-line" style={{ background: curve.color }} aria-hidden="true" />
            {curve.label}
          </span>
        ))}
      </p>
      <ChartFrame
        height={380}
        margin={margin}
        role="group"
        label={label}
        onPointer={(px, _py, inner) => {
          const x = linear(view.domain, [0, inner.width]);
          const target = x.invert(px);
          let best = 0;
          curves[0].points.forEach((point, i) => {
            if (Math.abs(point[view.field] - target) < Math.abs(curves[0].points[best][view.field] - target)) {
              best = i;
            }
          });
          setHover(best);
        }}
        onLeave={() => setHover(null)}
        overlay={({ width, margin: m }) => {
          if (hover == null) return null;
          const x = linear(view.domain, [0, width - m.left - m.right]);
          const anchor = Math.min(curves[0].points[hover][view.field], view.domain[1]);
          return (
            <Tooltip x={m.left + x(anchor)} y={m.top} width={width}>
              <div className="tip-title">Sample {hover + 1} of {steps}</div>
              {curves.map((curve) => (
                <Row
                  key={curve.key}
                  label={`${curve.label}, ${percent(curve.points[hover][view.field])} out`}
                  value={percent(curve.points[hover][field])}
                  color={curve.color}
                />
              ))}
            </Tooltip>
          );
        }}
      >
        {({ width, height }) => {
          const x = linear(view.domain, [0, width]);
          const y = linear(domain, [height, 0]);
          const band = width / steps;
          return (
            <g>
              <YAxis
                scale={y}
                ticks={ticks}
                width={width}
                format={(t) => percent(t, 0)}
                title={title}
                titleGap={wide ? 14 : 30}
              />
              <XAxis
                scale={x}
                ticks={view.ticks}
                height={height}
                width={width}
                margin={margin}
                format={(t) => percent(t, 0)}
                title={view.title}
              />
              {/* Where the section reads its comparison off: a quarter of the wire, or the connections that costs. */}
              <line x1={x(at)} x2={x(at)} y1={-6} y2={height} stroke="var(--rule-strong)" strokeDasharray="3 3" />
              <text className="direct-label" x={x(at) + 6} y={-8}>
                {mark}
              </text>
              {curves.map((curve) => (
                <path
                  key={curve.key}
                  data-mark="line"
                  pathLength="1"
                  d={line(
                    curve.points.filter(inside).map((point) => [x(point[view.field]), y(point[field])]),
                  )}
                  fill="none"
                  stroke={curve.color}
                  strokeWidth="2"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              ))}
              {indices.map((i) => {
                const anchor = curves[0].points[i][view.field];
                return (
                  <g key={i} {...rowProps(i)} role="img" aria-label={describe(curves, i, view)}>
                    <rect
                      className="row-band"
                      x={Math.min(x(anchor) - band / 2, width - band)}
                      width={band}
                      y={-2}
                      height={height + 4}
                      rx={3}
                    />
                    {hover === i &&
                      curves.map(
                        (curve) =>
                          inside(curve.points[i]) && (
                            <circle
                              key={curve.key}
                              cx={x(curve.points[i][view.field])}
                              cy={y(curve.points[i][field])}
                              r="4"
                              fill={curve.color}
                            />
                          ),
                      )}
                  </g>
                );
              })}
              {hover != null && (
                <line
                  x1={x(Math.min(curves[0].points[hover][view.field], view.domain[1]))}
                  x2={x(Math.min(curves[0].points[hover][view.field], view.domain[1]))}
                  y1={0}
                  y2={height}
                  stroke="var(--rule-strong)"
                />
              )}
            </g>
          );
        }}
      </ChartFrame>
    </>
  );
}

/** How much of the graph's sensory-to-motor efficiency survives as wire is taken from one end or the other. */
export default function Efficiency({ data, axis }) {
  const at = data.tradeoff.comparison.at_reference;
  return (
    <Curves
      data={data}
      axis={axis}
      field="efficiency_share"
      domain={[0, 1.02]}
      title="Efficiency, as a share of the whole graph"
      mark={axis === "wire" ? `${percent(at["longest first"].wire_removed_share, 0)} of the wire` : "matched count"}
      label={
        "Efficiency of the cell-type graph as connections are removed longest first, shortest first and at " +
        `random, against the ${axis === "wire" ? "wire" : "number of connections"} removed.`
      }
      describe={(curves, i, view) =>
        curves
          .map(
            (curve) =>
              `${curve.label}, ${percent(curve.points[i][view.field])} ${view.noun} out, efficiency ` +
              `${percent(curve.points[i].efficiency_share)}`,
          )
          .join("; ")
      }
    />
  );
}

/** The other measure, which barely moves: the share of nodes still in one weakly connected component. */
export function Component({ data }) {
  const at = data.tradeoff.comparison.at_reference;
  return (
    <Curves
      data={data}
      axis="wire"
      field="largest_component_share"
      domain={[0.75, 1.005]}
      ticks={COMPONENT_SHARES}
      title="Nodes in the largest component"
      mark={`${percent(at["longest first"].wire_removed_share, 0)} of the wire`}
      label={
        "Share of the cell types left in the largest weakly connected component as connections are removed " +
        "longest first, shortest first and at random, against the wire removed."
      }
      describe={(curves, i, view) =>
        curves
          .map(
            (curve) =>
              `${curve.label}, ${percent(curve.points[i][view.field])} ${view.noun} out, ` +
              `${percent(curve.points[i].largest_component_share)} of the nodes in one component`,
          )
          .join("; ")
      }
    />
  );
}

/** Every schedule at the reference point, and how much efficiency each one costs per metre of wire. */
export function EfficiencyTable({ data }) {
  const { comparison, curves, graph, baseline, sampling } = data.tradeoff;
  const at = comparison.at_reference;
  const half = comparison.wire_share_to_halve_efficiency;
  const spread = at["random, matched count"].efficiency_share_sd;
  return (
    <>
      <TableWrap label="Values behind Figure 14: the three schedules at a quarter of the wire removed">
        <table className="data">
          <caption>
            The first two rows are taken where each schedule has removed{" "}
            {percent(comparison.reference_wire_fraction, 0)} of the {metres(graph.total_wire_um)} of wire; the third
            is taken where the random schedule has removed the same number of connections as the longest-first one,
            and is the mean of {sampling.random_repeats} draws. Efficiency is the mean of 1/d over ordered pairs,
            estimated from {sampling.sources} sources drawn once and used at every point of every schedule; the
            whole graph stands at {fixed(baseline.efficiency, 4)}.
          </caption>
          <thead>
            <tr>
              <th scope="col">Schedule</th>
              <th scope="col" className="num-col">
                Connections removed
              </th>
              <th scope="col" className="num-col">
                Share of connections
              </th>
              <th scope="col" className="num-col">
                Wire removed
              </th>
              <th scope="col" className="num-col">
                Efficiency
              </th>
              <th scope="col" className="num-col">
                Share of the whole graph
              </th>
              <th scope="col" className="num-col">
                Largest component
              </th>
            </tr>
          </thead>
          <tbody>
            {SCHEDULES.map((schedule) => {
              const point = at[schedule.key];
              return (
                <tr key={schedule.key}>
                  <th scope="row">{schedule.label}</th>
                  <td className="num-col">{count(point.edges_removed)}</td>
                  <td className="num-col">{percent(point.edges_removed_share)}</td>
                  <td className="num-col">{metres(point.wire_removed_um)}</td>
                  <td className="num-col">{fixed(point.efficiency, 4)}</td>
                  <td className="num-col">
                    {percent(point.efficiency_share)}
                    {point.efficiency_share_sd ? ` ± ${percent(point.efficiency_share_sd)}` : ""}
                  </td>
                  <td className="num-col">{percent(point.largest_component_share)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </TableWrap>

      <TableWrap label="Values behind Figure 14: efficiency at every sampled point">
        <table className="data">
          <caption>
            Efficiency as a share of the whole graph at each of the {sampling.points} sampled points. Each row is
            named by the wire the longest-first schedule has removed; the shortest-first schedule has removed the
            same wire and the random schedule the same number of connections, so it has removed less.
          </caption>
          <thead>
            <tr>
              <th scope="col">Wire removed</th>
              {SCHEDULES.map((schedule) => (
                <th scope="col" className="num-col" key={schedule.key}>
                  {schedule.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {curves["longest first"].map((point, i) => (
              <tr key={point.wire_removed_share}>
                <th scope="row">{percent(point.wire_removed_share)}</th>
                {SCHEDULES.map((schedule) => (
                  <td className="num-col" key={schedule.key}>
                    {percent(curves[schedule.key][i].efficiency_share)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>

      <p className="caption">
        Per metre of wire removed that is {percent(comparison.efficiency_lost_per_metre["longest first"], 2)} of the
        starting efficiency lost from the long end against{" "}
        {percent(comparison.efficiency_lost_per_metre["shortest first"], 2)} from the short end, a factor of{" "}
        {fixed(
          comparison.efficiency_lost_per_metre["shortest first"] /
            comparison.efficiency_lost_per_metre["longest first"],
          1,
        )}
        . The median connection is {fixed(graph.median_length_um, 0)} µm long against a mean of{" "}
        {fixed(graph.mean_length_um, 0)} µm, so the same wire taken from the short end removes{" "}
        {fixed(at["shortest first"].edges_removed / at["longest first"].edges_removed, 1)} times as many
        connections. Matched on the number of connections instead, removing the longest leaves{" "}
        {percent(at["longest first"].efficiency_share)} against {percent(at["random, matched count"].efficiency_share)}{" "}
        ± {percent(spread)} at random. Efficiency falls to half its starting value after{" "}
        {percent(half["shortest first"])} of the wire is taken from the short end, and not within the range sampled
        from the long end.
      </p>
    </>
  );
}

/** The component measure at every sampled point, which is the null this figure reports. */
export function ComponentTable({ data }) {
  const { curves, baseline, graph } = data.tradeoff;
  return (
    <>
      <TableWrap label="Values behind Figure 15: the largest component at every sampled point">
        <table className="data">
          <caption>
            Share of the {count(graph.nodes)} cell types left in the largest weakly connected component. The whole
            graph holds {count(baseline.largest_component)} of them in one. Each row is named by the wire the
            longest-first schedule has removed; the random schedule is matched on the number of connections
            instead, so it has removed less wire at the same row.
          </caption>
          <thead>
            <tr>
              <th scope="col">Wire removed</th>
              {SCHEDULES.map((schedule) => (
                <th scope="col" className="num-col" key={schedule.key}>
                  {schedule.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {curves["longest first"].map((point, i) => (
              <tr key={point.wire_removed_share}>
                <th scope="row">{percent(point.wire_removed_share)}</th>
                {SCHEDULES.map((schedule) => (
                  <td className="num-col" key={schedule.key}>
                    {percent(curves[schedule.key][i].largest_component_share)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      <p className="caption">
        Component size is a blunt instrument at this density: efficiency has collapsed while the graph is still
        almost entirely one piece. That is a null for the component measure rather than evidence that the graph is
        robust in any useful sense.
      </p>
    </>
  );
}
