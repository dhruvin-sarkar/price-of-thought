import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { repoUrl } from "../lib/data.js";
import { useTheme } from "../lib/theme.js";

const LINKS = [
  ["placement", "Placement"],
  ["budget", "The budget"],
  ["connective", "The connective"],
  ["model", "A wiring model"],
  ["methods", "Methods"],
];

/** The mark: the brain over the nerve cord, joined by the one wire this study is about. */
function Mark() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
        <path d="M3.6 4.7h10.8" />
        <path d="M6.4 13.9h5.2" />
      </g>
      <path d="M9 4.7v9.2" fill="none" stroke="var(--field-wire)" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}

function ThemeIcon({ dark }) {
  return dark ? (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <path
        d="M13.2 10.1A5.6 5.6 0 0 1 5.9 2.8a5.6 5.6 0 1 0 7.3 7.3Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  ) : (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="8" r="3.1" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M8 1v1.6M8 13.4V15M1 8h1.6M13.4 8H15M3.05 3.05l1.13 1.13M11.82 11.82l1.13 1.13M12.95 3.05l-1.13 1.13M4.18 11.82l-1.13 1.13" />
      </g>
    </svg>
  );
}

/** Site bar; `ready` tells it the sections have rendered so it can mark the one being read. */
export default function Nav({ ready = true }) {
  const [current, setCurrent] = useState(null);
  const [theme, toggleTheme] = useTheme();
  const bar = useRef(null);

  // The links take a second row on a narrow screen, so the height anything scrolled to must clear is measured.
  useLayoutEffect(() => {
    const node = bar.current;
    if (!node) return undefined;
    const publish = () => document.documentElement.style.setProperty("--nav-bar", `${node.offsetHeight}px`);
    publish();
    const observer = new ResizeObserver(publish);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!ready) return undefined;
    let sections = [];
    const inBand = new Map();
    const spy = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => inBand.set(e.target, e.isIntersecting));
        const first = sections.find((s) => inBand.get(s));
        setCurrent(first ? first.id : null);
      },
      { rootMargin: "-40% 0px -55% 0px" },
    );
    // Sections can be replaced after first render; observe whichever elements currently carry the ids.
    const attach = () => {
      const next = LINKS.map(([id]) => document.getElementById(id)).filter(Boolean);
      if (next.length === sections.length && next.every((s, i) => s === sections[i])) return;
      spy.disconnect();
      inBand.clear();
      sections = next;
      sections.forEach((s) => spy.observe(s));
      if (!sections.length) setCurrent(null);
    };
    attach();
    const main = document.getElementById("main");
    const watcher = main ? new MutationObserver(attach) : null;
    watcher?.observe(main, { childList: true });
    return () => {
      watcher?.disconnect();
      spy.disconnect();
    };
  }, [ready]);

  return (
    <header className="nav" ref={bar}>
      <div className="wrap nav-inner">
        <a className="wordmark" href="#main">
          <Mark />
          The Price of Thought
        </a>
        <nav className="nav-links" aria-label="Sections">
          {LINKS.map(([id, label]) => (
            <a
              key={id}
              href={`#${id}`}
              className={current === id ? "is-current" : ""}
              aria-current={current === id ? "location" : undefined}
            >
              {label}
            </a>
          ))}
          <a className="nav-external" href={repoUrl}>
            Code and data
          </a>
        </nav>
        <button
          type="button"
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label={theme === "dark" ? "Switch to the light theme" : "Switch to the dark theme"}
        >
          <ThemeIcon dark={theme === "dark"} />
        </button>
      </div>
    </header>
  );
}
