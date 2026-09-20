import { useDeferredValue, useId, useMemo, useState } from "react";
import { Segmented } from "./ui.jsx";
import { blobUrl } from "../lib/data.js";
import { count, millimetre } from "../lib/format.js";

const SHOWN = 40;

const DIRECTIONS = [
  { value: "all", label: "Both" },
  { value: "descending", label: "Descending" },
  { value: "ascending", label: "Ascending" },
];

const COLUMNS = [
  { key: "cell_type", label: "Cell type", numeric: false },
  { key: "direction", label: "Direction", numeric: false },
  { key: "edges", label: "Connections", numeric: true },
  { key: "price_um", label: "Neck-crossing wire", numeric: true },
  { key: "value", label: "Flow lost when removed", numeric: true },
];

/** Every descending and ascending cell type, with what its neck-crossing wiring costs and what it carries. */
export default function Lookup({ data }) {
  const [query, setQuery] = useState("");
  const [direction, setDirection] = useState("all");
  const [sort, setSort] = useState({ key: "price_um", ascending: false });
  const searchId = useId();
  const deferred = useDeferredValue(query);

  const rows = useMemo(() => {
    const needle = deferred.trim().toLowerCase();
    const filtered = data.price.nodes.filter(
      (row) =>
        (direction === "all" || row.direction === direction) &&
        (!needle || row.cell_type.toLowerCase().includes(needle)),
    );
    const column = COLUMNS.find((c) => c.key === sort.key);
    return filtered.sort((a, b) => {
      const order = column.numeric
        ? a[sort.key] - b[sort.key]
        : String(a[sort.key]).localeCompare(String(b[sort.key]));
      return sort.ascending ? order : -order;
    });
  }, [data, deferred, direction, sort]);

  const toggle = (key) =>
    setSort((current) => ({ key, ascending: current.key === key ? !current.ascending : key === "cell_type" }));

  return (
    <div className="lookup">
      <div className="lookup-controls">
        <div className="lookup-search">
          <label className="field-label" htmlFor={searchId}>
            Find a cell type
          </label>
          <input
            id={searchId}
            className="input"
            type="search"
            placeholder="DNg98, AN07B004, DNpe"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <div>
          <span className="field-label" id="lookup-direction">
            Direction
          </span>
          <Segmented labelledBy="lookup-direction" options={DIRECTIONS} value={direction} onChange={setDirection} />
        </div>
      </div>

      <div className="table-wrap">
        <table className="data">
          <caption>
            {rows.length === data.price.nodes.length
              ? `All ${count(rows.length)} descending and ascending cell types by side.`
              : `${count(rows.length)} of ${count(data.price.nodes.length)} cell types match.`}
            {rows.length > SHOWN ? ` Showing the first ${SHOWN} in this order.` : ""}
          </caption>
          <thead>
            <tr>
              {COLUMNS.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={column.numeric ? "num-col" : undefined}
                  aria-sort={sort.key === column.key ? (sort.ascending ? "ascending" : "descending") : "none"}
                >
                  <button type="button" className="sort" onClick={() => toggle(column.key)}>
                    {column.label}
                    <span aria-hidden="true" className={sort.key === column.key ? "sort-mark is-on" : "sort-mark"}>
                      {sort.key === column.key && sort.ascending ? "↑" : "↓"}
                    </span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, SHOWN).map((row) => (
              <tr key={row.node}>
                <th scope="row">
                  <span className="id">{row.cell_type}</span> {row.side}
                </th>
                <td>{row.direction}</td>
                <td className="num-col">{count(row.edges)}</td>
                <td className="num-col">{millimetre(row.price_um)}</td>
                <td className="num-col">{count(row.value)}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length}>No cell type matches that name.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="caption">
        Price is the total length of a cell type&rsquo;s neck-crossing connections; value is the sensory-to-motor flow
        lost, in its own direction, when those connections alone are removed. Every row is in{" "}
        <a href={blobUrl("results/connective_price.csv")}>results/connective_price.csv</a>.
      </p>
    </div>
  );
}
