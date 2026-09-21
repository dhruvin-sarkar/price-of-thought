import { useCallback, useMemo, useSyncExternalStore } from "react";

export const NODE_HASH = "#lookup/";

/** The node name a `#lookup/<node>` address carries, or null. */
function readHash() {
  if (typeof window === "undefined" || !window.location.hash.startsWith(NODE_HASH)) return null;
  try {
    return decodeURIComponent(window.location.hash.slice(NODE_HASH.length)).trim() || null;
  } catch {
    return window.location.hash.slice(NODE_HASH.length).trim() || null;
  }
}

let target = readHash();
const listeners = new Set();

function onHash() {
  target = readHash();
  listeners.forEach((listener) => listener());
}

function subscribe(listener) {
  listeners.add(listener);
  if (listeners.size === 1) window.addEventListener("hashchange", onHash);
  return () => {
    listeners.delete(listener);
    if (!listeners.size) window.removeEventListener("hashchange", onHash);
  };
}

/** Index of the node a name picks out: its full node id, else the first node of a bare cell type. Separators are loose. */
export function resolveNode(nodes, name) {
  if (!name) return -1;
  const wanted = name.toLowerCase().replace(/[\s_-]+/g, "|");
  let bare = -1;
  for (let i = 0; i < nodes.length; i += 1) {
    const row = nodes[i];
    if (row.node.toLowerCase() === wanted) return i;
    if (bare < 0 && row.cell_type.toLowerCase() === wanted) bare = i;
  }
  return bare;
}

/**
 * Put `name` in the page address and tell every reader. replaceState fires no hashchange, so the change is
 * published here instead; the address is replaced rather than pushed, so the back button leaves the page.
 */
export function linkNode(name) {
  const { pathname, search } = window.location;
  window.history.replaceState(null, "", `${pathname}${search}${NODE_HASH}${encodeURIComponent(name)}`);
  target = name;
  listeners.forEach((listener) => listener());
}

/**
 * The connective node the page address names, shared by everything that shows one. `index` is its row in
 * `nodes` or -1, `name` is the address's own text so a caller can say when it matches nothing, and `select`
 * writes a row back to the address.
 */
export function useLinkedNode(nodes) {
  const name = useSyncExternalStore(subscribe, () => target, () => null);
  const index = useMemo(() => resolveNode(nodes, name), [nodes, name]);
  const select = useCallback(
    (row) => {
      if (row != null && row >= 0) linkNode(nodes[row].node);
    },
    [nodes],
  );
  return { name, index, select };
}
