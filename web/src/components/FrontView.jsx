import { useMemo } from "react";
import { rampColor } from "../lib/scales.js";

/** The dark theme's length ramp, the one the title plate and the connective view use on the black field. */
const RAMP = ["#4a1a08", "#b23a10", "#eb6834", "#f7cfae"];
const BOX = 1000;

/**
 * The still front view the title plate draws: the neuropil silhouette with a sample of the neck-crossing
 * connections through it, coloured by length. Stands in for the rotatable view until that has loaded, and
 * stays for a reader who never asks for it. Mirrors front_layer in pipeline/readme_assets.py.
 */
export default function FrontView({ front }) {
  const { outlines, runs } = useMemo(() => {
    const [lo, hi] = [front.bounds.min, front.bounds.max];
    const scale = BOX / Math.max(hi[0] - lo[0], hi[1] - lo[1]);
    const ox = (BOX - (hi[0] - lo[0]) * scale) / 2;
    const oy = (BOX - (hi[1] - lo[1]) * scale) / 2;
    const round = (v) => Math.round(v * 10) / 10;
    const at = (x, y) => [round(ox + (x - lo[0]) * scale), round(oy + (hi[1] - y) * scale)];

    const shapes = front.outlines.map((outline) => outline.map(([x, y]) => at(x, y).join(",")).join(" "));

    // Wires of one colour share a path, as they do in the committed plate, so the browser draws a few dozen
    // paths rather than three thousand.
    const [a, b] = front.length_range_um;
    const byColour = [];
    for (const [x1, y1, x2, y2, length] of front.wires) {
      const colour = rampColor(RAMP, (length - a) / (b - a));
      const [p, q] = at(x1, y1);
      const [r, s] = at(x2, y2);
      if (!byColour.length || byColour[byColour.length - 1].colour !== colour) {
        byColour.push({ colour, key: `${colour}-${byColour.length}`, d: "" });
      }
      byColour[byColour.length - 1].d += `M${p} ${q}L${r} ${s}`;
    }
    return { outlines: shapes, runs: byColour };
  }, [front]);

  return (
    <svg className="front-view" viewBox={`0 0 ${BOX} ${BOX}`} aria-hidden="true" focusable="false">
      {outlines.map((points, i) => (
        <polygon key={i} points={points} fill="#1b1c18" stroke="#3a3b34" strokeWidth="2" />
      ))}
      {runs.map((run) => (
        <path
          key={run.key}
          d={run.d}
          stroke={run.colour}
          strokeWidth="1.6"
          strokeOpacity="0.62"
          strokeLinecap="round"
          fill="none"
        />
      ))}
    </svg>
  );
}
