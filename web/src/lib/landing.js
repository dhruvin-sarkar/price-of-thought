import { useEffect } from "react";

// Hold a deep link against the page above it for this long after it last changed height, and never past the limit.
const QUIET_MS = 3000;
const LIMIT_MS = 10000;
const HANDOVER = ["wheel", "touchstart", "keydown", "pointerdown"];

function hashId(hash) {
  try {
    return decodeURIComponent(hash.slice(1));
  } catch {
    return hash.slice(1);
  }
}

/**
 * Element a location hash names: whatever carries that id, or for a compound hash such as `#lookup/DNg98_L`,
 * which names a row inside a section rather than an element, the section it sits in.
 */
export function hashTarget(hash) {
  if (!hash || hash.length < 2) return null;
  const id = hashId(hash);
  const exact = document.getElementById(id);
  if (exact || !id.includes("/")) return exact;
  return document.getElementById(id.slice(0, id.indexOf("/")));
}

/**
 * Lands a cold load on the section its hash names. The results arrive after first paint, so at the moment the
 * browser would jump there is nothing to jump to; this waits for the sections and then keeps the target in place
 * while the figures above it size themselves. It hands the page back as soon as the reader scrolls, touches,
 * clicks or types, and lets go once the main element has held its height for a few seconds. The jump is instant,
 * and scroll-padding-top clears the sticky bar.
 */
export function useHashLanding(ready) {
  useEffect(() => {
    const main = document.getElementById("main");
    const { hash } = window.location;
    if (!ready || !main || hash.length < 2) return undefined;

    let quiet = null;
    let observer = null;
    const limit = setTimeout(() => release(), LIMIT_MS);

    function release() {
      observer?.disconnect();
      observer = null;
      clearTimeout(quiet);
      clearTimeout(limit);
      HANDOVER.forEach((type) => window.removeEventListener(type, release));
    }

    // Called from the ResizeObserver, where layout is already settled, so reading the target forces no reflow.
    function land() {
      if (window.location.hash !== hash) {
        release();
        return;
      }
      const target = hashTarget(hash);
      if (!target) return;
      target.scrollIntoView({ block: "start", inline: "nearest", behavior: "instant" });
      clearTimeout(quiet);
      quiet = setTimeout(release, QUIET_MS);
    }

    observer = new ResizeObserver(land);
    observer.observe(main);
    HANDOVER.forEach((type) => window.addEventListener(type, release, { passive: true }));
    return release;
  }, [ready]);

  // A compound hash matches no element id, so the browser does nothing for it on its own.
  useEffect(() => {
    const onHash = () => {
      const { hash } = window.location;
      if (hash.length < 2 || document.getElementById(hashId(hash))) return;
      hashTarget(hash)?.scrollIntoView({ block: "start" });
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
}
