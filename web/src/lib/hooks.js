import { useEffect, useLayoutEffect, useRef, useState } from "react";

export function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return reduced;
}

/** True while a media query matches, kept in step with it. */
export function useMedia(query) {
  const [matches, setMatches] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const list = window.matchMedia(query);
    const update = () => setMatches(list.matches);
    update();
    list.addEventListener("change", update);
    return () => list.removeEventListener("change", update);
  }, [query]);
  return matches;
}

// One observer for every measured element, so a resize reaches all charts in a single callback and one render.
const widthListeners = new Map();
let widthObserver = null;

function observeWidth(node, listener) {
  widthObserver ??= new ResizeObserver((entries) => {
    for (const entry of entries) {
      let width = Math.round(entry.contentRect.width);
      // Layout is clean inside the callback, so reading the parent here does not force a reflow.
      if (width <= 0) width = Math.round(entry.target.parentElement?.clientWidth ?? 0);
      widthListeners.get(entry.target)?.(width);
    }
  });
  widthListeners.set(node, listener);
  widthObserver.observe(node);
  return () => {
    widthListeners.delete(node);
    widthObserver.unobserve(node);
  };
}

/**
 * Content width of an element, tracked with a shared ResizeObserver. The first width arrives with the observer's
 * first callback, after layout and before paint; until then the hook returns `fallback`.
 */
export function useWidth(fallback = 0) {
  const ref = useRef(null);
  const [width, setWidth] = useState(fallback);
  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    return observeWidth(node, (next) => {
      if (next > 0) setWidth(next);
    });
  }, []);
  return [ref, width];
}

const nearListeners = new Map();
let nearObserver = null;

function observeNear(node, listener) {
  nearObserver ??= new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const done = nearListeners.get(entry.target);
        nearListeners.delete(entry.target);
        nearObserver.unobserve(entry.target);
        done?.();
      }
    },
    { rootMargin: "150% 0px" },
  );
  nearListeners.set(node, listener);
  nearObserver.observe(node);
  return () => {
    nearListeners.delete(node);
    nearObserver.unobserve(node);
  };
}

/**
 * True once the element referenced by `ref` has come within about one and a half screens of the viewport, and from
 * then on. Drawing waits for it; layout must not, so callers keep the element's size fixed either way.
 */
export function useNear(ref) {
  const [near, setNear] = useState(() => typeof IntersectionObserver === "undefined");
  useLayoutEffect(() => {
    const node = ref.current;
    if (near || !node) return undefined;
    return observeNear(node, () => setNear(true));
  }, [ref, near]);
  return near;
}
