const MINUS = "\u2212";
const GROUPED = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

/** A number to `digits` decimals, with a typographic minus for negatives. */
export const fixed = (value, digits = 2) =>
  value == null || Number.isNaN(value) ? "n/a" : Number(value).toFixed(digits).replace("-", MINUS);

export const count = (value) => (value == null ? "n/a" : GROUPED.format(Math.round(value)));

export const percent = (value, digits = 1) =>
  value == null || Number.isNaN(value) ? "n/a" : `${(100 * value).toFixed(digits)}%`;

/** A ratio against a null or a baseline, as the results files report it. */
export const times = (value, digits = 2) => `${fixed(value, digits)}\u00d7`;

export const micron = (value, digits = 0) => `${fixed(value, digits)} \u00b5m`;

/** Micrometres shown as millimetres, for totals where µm would run to eight digits. */
export const millimetre = (value_um, digits = 0) => `${count(Number(value_um) / 1000)} mm`;

export const signed = (value, digits = 3) =>
  value > 0 ? `+${fixed(value, digits)}` : fixed(value, digits);

/** p-value: "< 0.001" below 0.001, three decimals below 0.1, two decimals above. */
export function pValue(p) {
  if (p == null || Number.isNaN(p)) return "n/a";
  if (p < 0.001) return "< 0.001";
  if (p < 0.1) return p.toFixed(3);
  return p.toFixed(2);
}

/** p-value as a clause for running text: "p = 0.036", or "p < 0.001". */
export function pClause(p) {
  const text = pValue(p);
  return text.startsWith("<") ? `p ${text}` : `p = ${text}`;
}

/** Text with its first letter capitalized, for the start of a sentence or a label. */
export const sentence = (text) => (text ? `${text[0].toUpperCase()}${text.slice(1)}` : text);

const SUPERCLASS_NAMES = {
  ascending_neuron: "ascending",
  cb_intrinsic: "central brain intrinsic",
  descending_neuron: "descending",
  vnc_intrinsic: "nerve cord intrinsic",
};

export const superclassName = (id) => SUPERCLASS_NAMES[id] ?? String(id).replaceAll("_", " ");

const PROPERTY_NAMES = {
  in_degree_sd: "in-degree, SD",
  in_degree_max: "in-degree, maximum",
  out_degree_sd: "out-degree, SD",
  out_degree_max: "out-degree, maximum",
  total_cost_um: "total wiring length",
  median_length_um: "median connection length",
  cross_compartment_fraction: "share joining brain and cord",
  reciprocity: "reciprocity",
  transitivity: "transitivity",
  flow: "sensory-to-motor flow",
  pairs: "reachable sensory-motor pairs",
  neck_crossing_edges: "neck-crossing connections",
  rich_routes: "rich-to-rich routes",
};

export const propertyName = (id) => PROPERTY_NAMES[id] ?? String(id).replaceAll("_", " ");

/** How a graph property is written out, so real and synthetic values are formatted the same way. */
export function propertyValue(id, value) {
  if (id === "total_cost_um") return millimetre(value);
  if (id === "median_length_um") return micron(value, 1);
  if (id === "cross_compartment_fraction") return percent(value, 2);
  if (id === "reciprocity" || id === "transitivity") return fixed(value, 4);
  if (id === "in_degree_sd" || id === "out_degree_sd") return fixed(value, 2);
  return count(value);
}
