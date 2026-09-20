/** Linear scale from a data domain to a pixel range, with `invert`. */
export function linear([d0, d1], [r0, r1]) {
  const span = d1 - d0 || 1;
  const s = (value) => r0 + ((value - d0) / span) * (r1 - r0);
  s.invert = (pixel) => d0 + ((pixel - r0) / (r1 - r0 || 1)) * span;
  s.domain = [d0, d1];
  s.range = [r0, r1];
  return s;
}

/** Base-10 logarithmic scale; the domain must be positive. */
export function log([d0, d1], [r0, r1]) {
  const l0 = Math.log10(d0);
  const l1 = Math.log10(d1);
  const s = (value) => r0 + ((Math.log10(value) - l0) / (l1 - l0 || 1)) * (r1 - r0);
  s.invert = (pixel) => 10 ** (l0 + ((pixel - r0) / (r1 - r0 || 1)) * (l1 - l0));
  s.domain = [d0, d1];
  s.range = [r0, r1];
  return s;
}

/** Round tick values covering a domain, about `target` of them. */
export function niceTicks([d0, d1], target = 5, { integer = false } = {}) {
  const span = d1 - d0;
  if (span <= 0) return [d0];
  const raw = span / target;
  const power = 10 ** Math.floor(Math.log10(raw));
  const multiples = integer ? [1, 2, 5, 10] : [1, 2, 2.5, 5, 10];
  let step = multiples.map((m) => m * power).find((s) => s >= raw) ?? raw;
  // A tick that formats as a whole number must be one, or an axis of counts prints 2.5 and 7.5 as 3 and 8.
  if (integer) step = Math.max(1, Math.round(step));
  const out = [];
  for (let v = Math.ceil(d0 / step - 1e-9) * step; v <= d1 + step * 1e-6; v += step) out.push(Number(v.toFixed(10)));
  return out;
}

/** Powers of ten inside a positive domain. */
export function logTicks([d0, d1]) {
  const out = [];
  for (let e = Math.floor(Math.log10(d0)); e <= Math.ceil(Math.log10(d1)); e += 1) {
    const v = 10 ** e;
    if (v >= d0 * 0.999 && v <= d1 * 1.001) out.push(v);
  }
  return out;
}

/** SVG path through points already in pixel space. */
export const line = (points) => points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join("");

/** Closed SVG path for a band between an upper and a lower series. */
export const band = (upper, lower) =>
  `${line(upper)}L${lower
    .slice()
    .reverse()
    .map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`)
    .join("L")}Z`;

/** Index of the value in a sorted array nearest to `target`. */
export function nearestIndex(values, target) {
  let best = 0;
  let distance = Infinity;
  for (let i = 0; i < values.length; i += 1) {
    const d = Math.abs(values[i] - target);
    if (d < distance) {
      distance = d;
      best = i;
    }
  }
  return best;
}

/** Colour at position `t` in [0, 1] along evenly spaced hex stops. */
export function rampColor(stops, t) {
  const x = Math.min(Math.max(t, 0), 1) * (stops.length - 1);
  const i = Math.min(Math.floor(x), stops.length - 2);
  const f = x - i;
  const channel = (c) => {
    const a = parseInt(stops[i].slice(1 + c * 2, 3 + c * 2), 16);
    const b = parseInt(stops[i + 1].slice(1 + c * 2, 3 + c * 2), 16);
    return Math.round(a + (b - a) * f);
  };
  return `rgb(${channel(0)} ${channel(1)} ${channel(2)})`;
}
