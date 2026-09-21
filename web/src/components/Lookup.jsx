import { useCallback, useDeferredValue, useEffect, useId, useMemo, useRef, useState } from "react";
import { Segmented, TableWrap } from "./ui.jsx";
import { blobUrl } from "../lib/data.js";
import { count, fixed, percent } from "../lib/format.js";
import { NODE_HASH, useLinkedNode } from "../lib/nodeLink.js";
import "../styles/lookup.css";

const SUGGESTIONS = 8;

const SIDES = { L: "left", R: "right", M: "midline" };

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
  { key: "per_mm", label: "Flow per mm", numeric: true },
];

/** Millimetres to two decimals: the shortest nodes hold a fifth of one and must not round to zero. */
const wire = (um) => `${fixed(um / 1000, 2)} mm`;

/** Share of peers a node stands above, floored: only a node above every peer is allowed to read 100%. */
const over = (share) => `${Math.floor(100 * share)}%`;

/** Flow bought per millimetre of neck-crossing wire, the ratio results/connective_price.csv reports. */
const perMm = (row) => row.value / (row.price_um / 1000);

const nodeLabel = (row) => `${row.cell_type} ${row.side}`;

/** Prefix matches first, shortest name first; then substring matches by where the match falls. */
function search(entries, query) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const prefix = [];
  const inside = [];
  for (let i = 0; i < entries.length; i += 1) {
    const at = entries[i].key.indexOf(q);
    if (at === 0) prefix.push(i);
    else if (at > 0) inside.push([i, at]);
  }
  const byName = (a, b) =>
    entries[a].key.length - entries[b].key.length || entries[a].key.localeCompare(entries[b].key);
  prefix.sort(byName);
  if (prefix.length >= SUGGESTIONS) return prefix.slice(0, SUGGESTIONS);
  inside.sort((a, b) => a[1] - b[1] || byName(a[0], b[0]));
  return [...prefix, ...inside.map(([i]) => i)].slice(0, SUGGESTIONS);
}

function Marked({ text, query }) {
  const q = query.trim().toLowerCase();
  const at = q ? text.toLowerCase().indexOf(q) : -1;
  if (at < 0) return text;
  return (
    <>
      {text.slice(0, at)}
      <mark>{text.slice(at, at + q.length)}</mark>
      {text.slice(at + q.length)}
    </>
  );
}

/**
 * Every descending and ascending cell type on one side, with what its neck-crossing wiring costs and what it
 * carries. Search by name, sort by any column, or open a node's ledger against the rest of its direction.
 */
export default function Lookup({ data }) {
  const nodes = data.price.nodes;
  const tests = data.price.tests;

  const [query, setQuery] = useState("");
  const [direction, setDirection] = useState("all");
  const [sort, setSort] = useState({ key: "price_um", ascending: false });
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [roving, setRoving] = useState(0);

  const base = useId().replace(/[^a-zA-Z0-9]/g, "");
  const deferred = useDeferredValue(query);
  const scroller = useRef(null);

  const entries = useMemo(
    () => nodes.map((row, index) => ({ key: nodeLabel(row).toLowerCase(), row, index })),
    [nodes],
  );
  const indexByNode = useMemo(() => new Map(nodes.map((row, i) => [row.node, i])), [nodes]);

  // The page address holds the selection, so the hero and this table always show the same node.
  const { name: linked, index: selected, select } = useLinkedNode(nodes);
  // A linked name matching no node; the address is left as the reader received it.
  const unknown = linked && selected < 0 ? linked : null;

  const rows = useMemo(() => {
    const needle = deferred.trim().toLowerCase();
    const filtered = nodes.filter(
      (row) =>
        (direction === "all" || row.direction === direction) &&
        (!needle || nodeLabel(row).toLowerCase().includes(needle)),
    );
    const column = COLUMNS.find((c) => c.key === sort.key);
    const value = (row) => (sort.key === "per_mm" ? perMm(row) : row[sort.key]);
    return filtered.sort((a, b) => {
      const order = column.numeric
        ? value(a) - value(b) || a.cell_type.localeCompare(b.cell_type)
        : String(value(a)).localeCompare(String(value(b))) || a.side.localeCompare(b.side);
      return sort.ascending ? order : -order;
    });
  }, [nodes, deferred, direction, sort]);

  const suggestions = useMemo(() => search(entries, query), [entries, query]);
  const listOpen = open && query.trim().length > 0;

  const countText =
    rows.length === nodes.length
      ? `All ${count(nodes.length)} nodes listed.`
      : `${count(rows.length)} of ${count(nodes.length)} nodes match.`;
  const [announced, setAnnounced] = useState(countText);
  useEffect(() => {
    const timer = setTimeout(() => setAnnounced(countText), 400);
    return () => clearTimeout(timer);
  }, [countText]);

  const choose = useCallback(
    (index) => {
      if (index == null || index < 0) return;
      setQuery("");
      setOpen(false);
      setActive(-1);
      select(index);
    },
    [select],
  );

  // A node hidden by the direction filter would be selected with nothing on screen to show for it. This runs
  // for a selection made anywhere, including one arriving from the hero or from a link the reader followed.
  useEffect(() => {
    if (selected < 0) return;
    setDirection((current) => (current === "all" || current === nodes[selected].direction ? current : "all"));
  }, [selected, nodes]);

  useEffect(() => {
    if (active >= 0) document.getElementById(`${base}-option-${active}`)?.scrollIntoView({ block: "nearest" });
  }, [active, base]);

  // Bring the selected row into the table's own scroller without moving the page under the reader.
  useEffect(() => {
    const box = scroller.current;
    const row = box?.querySelector('[data-selected="true"]');
    if (!box || !row) return;
    const top = row.offsetTop;
    const bottom = top + row.offsetHeight;
    if (top < box.scrollTop) box.scrollTop = Math.max(0, top - box.clientHeight / 3);
    else if (bottom > box.scrollTop + box.clientHeight) box.scrollTop = bottom - box.clientHeight / 1.5;
  }, [selected, rows]);

  function onSearchKeyDown(event) {
    if (event.nativeEvent.isComposing) return;
    const n = suggestions.length;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      if (n) setActive((a) => (a + 1) % n);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      if (n) setActive((a) => (a <= 0 ? n - 1 : a - 1));
    } else if (event.key === "Enter") {
      if (listOpen && n) {
        event.preventDefault();
        choose(entries[suggestions[active >= 0 ? active : 0]].index);
      }
    } else if (event.key === "Escape") {
      if (listOpen) {
        event.preventDefault();
        setOpen(false);
        setActive(-1);
      } else if (query) {
        event.preventDefault();
        setQuery("");
      }
    }
  }

  const position = Math.min(roving, Math.max(0, rows.length - 1));

  function onRowsKeyDown(event) {
    const last = rows.length - 1;
    if (last < 0) return;
    let next;
    if (event.key === "Home") next = 0;
    else if (event.key === "End") next = last;
    else {
      const step = { ArrowDown: 1, ArrowUp: -1, PageDown: 10, PageUp: -10 }[event.key];
      if (!step) return;
      next = Math.max(0, Math.min(last, position + step));
    }
    event.preventDefault();
    setRoving(next);
    document.getElementById(`${base}-row-${next}`)?.focus();
  }

  const toggle = (key) =>
    setSort((current) => ({ key, ascending: current.key === key ? !current.ascending : key === "cell_type" }));

  const node = selected >= 0 ? nodes[selected] : null;

  return (
    <div className="lk">
      <div className="lk-controls">
        <div className="lk-search">
          <label className="field-label" htmlFor={`${base}-input`} id={`${base}-label`}>
            Find a cell type
          </label>
          <input
            id={`${base}-input`}
            className="input"
            type="text"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={listOpen}
            aria-controls={`${base}-listbox`}
            aria-activedescendant={listOpen && active >= 0 ? `${base}-option-${active}` : undefined}
            autoComplete="off"
            autoCapitalize="off"
            spellCheck={false}
            placeholder="DNg98, AN07B004, DNpe"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setOpen(true);
              setActive(-1);
            }}
            onFocus={() => query && setOpen(true)}
            onBlur={() => setOpen(false)}
            onKeyDown={onSearchKeyDown}
          />
          <ul
            className="lk-listbox"
            id={`${base}-listbox`}
            role="listbox"
            aria-labelledby={`${base}-label`}
            hidden={!listOpen}
          >
            {suggestions.map((i, k) => {
              const row = entries[i].row;
              return (
                <li
                  key={row.node}
                  id={`${base}-option-${k}`}
                  role="option"
                  aria-selected={k === active}
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseEnter={() => setActive(k)}
                  onClick={() => choose(entries[i].index)}
                >
                  <span className="id">
                    <Marked text={row.cell_type} query={query} />
                  </span>
                  <span className="lk-option-meta">
                    {SIDES[row.side] ?? row.side}, {row.direction}
                  </span>
                </li>
              );
            })}
            {listOpen && suggestions.length === 0 && (
              <li className="lk-empty" role="presentation">
                No cell type name contains &ldquo;{query.trim()}&rdquo;.
              </li>
            )}
          </ul>
        </div>
        <div>
          <span className="field-label" id={`${base}-direction`}>
            Direction
          </span>
          <Segmented
            labelledBy={`${base}-direction`}
            options={DIRECTIONS}
            value={direction}
            onChange={setDirection}
          />
        </div>
      </div>

      {unknown && (
        <p className="lk-unknown" role="status">
          No node is named &ldquo;{unknown}&rdquo;. Search for another name above, or pick a row from the table.
          Names run <span className="id">DNg98</span> for a cell type and <span className="id">DNg98|L</span> for one
          side of it.
        </p>
      )}

      {node ? (
        <Ledger node={node} nodes={nodes} tests={tests} />
      ) : (
        <p className="lk-empty-note">
          Search for a cell type, or select a row below, to see what its neck-crossing wire costs and what it buys
          against the rest of its direction.
        </p>
      )}

      <p className="lk-count">
        {/* The count is read from the live region instead, so typing does not announce the sentence twice. */}
        <span aria-hidden="true">{countText}</span> Select a row to open its ledger.
      </p>
      <p className="visually-hidden" aria-live="polite">
        {announced}
      </p>

      <div
        ref={scroller}
        className="lk-scroll"
        tabIndex={0}
        role="region"
        aria-label="Every connective node, by cell type and side"
      >
        <table className="data lk-table">
          <caption className="visually-hidden">
            Every descending and ascending cell type by side, with its neck-crossing connections, the wire they
            hold, the flow lost when they are removed, and the flow that buys per millimetre.
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
                  <button type="button" className="lk-sort" onClick={() => toggle(column.key)}>
                    {column.label}
                    <span aria-hidden="true" className={sort.key === column.key ? "lk-mark is-on" : "lk-mark"}>
                      {sort.key === column.key && sort.ascending ? "↑" : "↓"}
                    </span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody onKeyDown={onRowsKeyDown}>
            {rows.map((row, k) => {
              const on = node != null && row.node === node.node;
              return (
                <tr key={row.node} className={on ? "is-on" : undefined} data-selected={on ? "true" : undefined}>
                  <th scope="row">
                    <button
                      type="button"
                      id={`${base}-row-${k}`}
                      className="lk-row"
                      tabIndex={k === position ? 0 : -1}
                      aria-pressed={on}
                      onFocus={() => setRoving(k)}
                      onClick={() => choose(indexByNode.get(row.node))}
                    >
                      <span className="id">
                        <Marked text={row.cell_type} query={deferred} />
                      </span>{" "}
                      {row.side}
                    </button>
                  </th>
                  <td>{row.direction}</td>
                  <td className="num-col">{count(row.edges)}</td>
                  <td className="num-col">{wire(row.price_um)}</td>
                  <td className="num-col">{count(row.value)}</td>
                  <td className="num-col">{fixed(perMm(row), 2)}</td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length}>No node matches that name in this direction.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="caption">
        Value is the sensory-to-motor flow lost, in its own direction, when a node&rsquo;s neck-crossing connections
        alone are removed. Arrow keys move down the table, Enter opens a row. Every row is in{" "}
        <a href={blobUrl("results/connective_price.csv")}>results/connective_price.csv</a>.
      </p>
    </div>
  );
}

/** What one node costs and what it buys, set against every other node running the same way across the neck. */
function Ledger({ node, nodes, tests }) {
  const test = tests[node.direction];
  const total = tests.descending.total_price_um + tests.ascending.total_price_um;

  const peers = useMemo(() => {
    const group = nodes.filter((row) => row.direction === node.direction);
    const place = (key, value) => {
      let above = 0;
      let below = 0;
      for (const row of group) {
        const other = key === "per_mm" ? perMm(row) : row[key];
        if (other > value) above += 1;
        else if (other < value) below += 1;
      }
      return { rank: above + 1, share: group.length > 1 ? below / (group.length - 1) : 0 };
    };
    return {
      n: group.length,
      price: place("price_um", node.price_um),
      value: place("value", node.value),
      sides: group
        .filter((row) => row.cell_type === node.cell_type)
        .sort((a, b) => a.side.localeCompare(b.side)),
    };
  }, [node, nodes]);

  const bought = node.value > 0;

  return (
    <article className="lk-ledger" aria-labelledby={`${node.node}-name`}>
      <header className="lk-ledger-head">
        <h4 className="lk-name" id={`${node.node}-name`}>
          <span className="id">{node.cell_type}</span>
        </h4>
        <p className="lk-ledger-meta">
          <span>{SIDES[node.side] ?? node.side} side</span>
          <span>{node.direction} across the neck</span>
        </p>
      </header>

      <dl className="lk-facts">
        <div>
          <dt>Neck-crossing connections</dt>
          <dd>{count(node.edges)}</dd>
        </div>
        <div>
          <dt>Wire they hold</dt>
          <dd>{wire(node.price_um)}</dd>
        </div>
        <div>
          <dt>Flow lost when removed</dt>
          <dd>{count(node.value)}</dd>
        </div>
        <div>
          <dt>Flow per mm of wire</dt>
          <dd>{fixed(perMm(node), 2)}</dd>
        </div>
      </dl>

      <p className="lk-read">
        Its neck-crossing connections hold {percent(node.price_um / total, 2)} of all the wire that crosses the neck.{" "}
        {bought ? (
          <>
            Removing them costs {count(node.value)} units of {node.direction} flow. Measured the same way, one node
            at a time, the {count(test.n)} {node.direction} nodes lose {count(test.total_value)} units between them.
          </>
        ) : (
          <>
            Removing them costs no flow at all, as it does for {count(test.zero_value)} of the {count(test.n)}{" "}
            {node.direction} nodes: another route carries what they carried.
          </>
        )}
      </p>

      <div className="lk-peers">
        <Peer
          label="Wire held"
          text={`Rank ${count(peers.price.rank)} of ${count(peers.n)}, above ${over(peers.price.share)} of them`}
          share={peers.price.share}
        />
        <Peer
          label="Flow bought"
          text={
            bought
              ? `Rank ${count(peers.value.rank)} of ${count(peers.n)}, above ${over(peers.value.share)} of them`
              : `Level with the ${count(test.zero_value)} nodes that buy none`
          }
          share={peers.value.share}
        />
      </div>
      <p className="caption lk-peer-note">
        Each bar is the share of {node.direction} nodes this one stands above: none at the left, all of them at the
        right, the short rule halfway. Ranks count every {node.direction} node, {count(peers.n)} of them.
      </p>

      {peers.sides.length > 1 && (
        <div className="lk-sides">
          <h5 className="lk-sides-title">
            The same cell type on each side
          </h5>
          <TableWrap label={`Connections, wire and flow for each side of ${node.cell_type}`}>
            <table className="data">
              <caption className="visually-hidden">
                Connections, wire and flow for each side of {node.cell_type}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Side</th>
                  <th scope="col" className="num-col">
                    Connections
                  </th>
                  <th scope="col" className="num-col">
                    Wire
                  </th>
                  <th scope="col" className="num-col">
                    Flow lost
                  </th>
                  <th scope="col" className="num-col">
                    Flow per mm
                  </th>
                </tr>
              </thead>
              <tbody>
                {peers.sides.map((row) => (
                  <tr key={row.node} className={row.node === node.node ? "is-on" : undefined}>
                    <th scope="row">{SIDES[row.side] ?? row.side}</th>
                    <td className="num-col">{count(row.edges)}</td>
                    <td className="num-col">{wire(row.price_um)}</td>
                    <td className="num-col">{count(row.value)}</td>
                    <td className="num-col">{fixed(perMm(row), 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
          <p className="caption">
            The two sides are counted separately throughout, so the gap between them is the spread to expect within
            one cell type.
          </p>
        </div>
      )}

      <p className="caption lk-share">
        This node is in the page address, so the link opens on it again:{" "}
        <span className="id">{`${NODE_HASH}${node.node}`}</span>
      </p>
    </article>
  );
}

function Peer({ label, text, share }) {
  const at = `${(100 * Math.min(1, Math.max(0, share))).toFixed(1)}%`;
  return (
    <div className="lk-peer">
      <div className="lk-peer-head">
        <span className="label">{label}</span>
        <span className="lk-peer-text">{text}</span>
      </div>
      <div className="lk-track" aria-hidden="true">
        <span className="lk-fill" style={{ width: at }} />
        <span className="lk-half" />
        <span className="lk-dot" style={{ left: at }} />
      </div>
    </div>
  );
}
