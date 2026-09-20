import { createContext, useContext, useId, useRef } from "react";

/** Heading level for titles rendered by Figure; sections set it for what they contain. */
export const HeadingContext = createContext(3);

export function HeadingLevel({ level, children }) {
  return <HeadingContext.Provider value={level}>{children}</HeadingContext.Provider>;
}

/** Heading tag for an explicit level or the level from context, kept within h2 to h6. */
export function useHeading(level) {
  const context = useContext(HeadingContext);
  const resolved = Math.min(6, Math.max(2, level ?? context));
  return { level: resolved, Tag: `h${resolved}` };
}

/**
 * A figure: its number and title with optional controls on the right, the graphic, and a caption on how to read
 * it. The number counts itself with a CSS counter; pass `number` to set it explicitly, matching the README.
 * The number is hidden from assistive technology, so the figure is named by its title alone.
 * `variant="field"` sets the figure on the black field.
 */
export function Figure({ id, number, title, controls, caption, children, variant = "", className = "", level }) {
  const fallback = useId();
  const titleId = `${id ?? fallback}-title`;
  const { Tag } = useHeading(level);
  return (
    <figure
      id={id}
      className={`figure ${variant === "field" ? "figure-field field" : ""} ${className}`.trim()}
      aria-labelledby={titleId}
    >
      <div className="figure-head">
        <Tag id={titleId} className="figure-title">
          <span className="figure-number" aria-hidden="true">
            {number != null ? `Figure ${number}` : null}
          </span>
          {title}
        </Tag>
        {controls && <div className="figure-controls">{controls}</div>}
      </div>
      <div className="figure-body">{children}</div>
      {caption && <figcaption className="figure-caption">{caption}</figcaption>}
    </figure>
  );
}

/**
 * Exclusive choice as a washed track of buttons; arrow keys, Home and End move the choice.
 * Name the group with `label`, or with `labelledBy` pointing at a visible label's id.
 */
export function Segmented({ label, labelledBy, options, value, onChange }) {
  const refs = useRef([]);
  const current = options.findIndex((o) => o.value === value);
  const onKeyDown = (event) => {
    const last = options.length - 1;
    let next;
    if (event.key === "Home") next = 0;
    else if (event.key === "End") next = last;
    else {
      const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
      if (!step) return;
      next = (Math.max(current, 0) + step + options.length) % options.length;
    }
    event.preventDefault();
    onChange(options[next].value);
    refs.current[next]?.focus();
  };
  return (
    <div
      className="segmented"
      role="radiogroup"
      aria-label={labelledBy ? undefined : label}
      aria-labelledby={labelledBy}
      onKeyDown={onKeyDown}
    >
      {options.map((option, i) => (
        <button
          key={option.value}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="button"
          role="radio"
          aria-checked={option.value === value}
          tabIndex={option.value === value || (current < 0 && i === 0) ? 0 : -1}
          className={option.value === value ? "on" : ""}
          onClick={() => onChange(option.value)}
        >
          {option.color && <span className="swatch" style={{ background: option.color }} aria-hidden="true" />}
          {option.label}
        </button>
      ))}
    </div>
  );
}

/** Prose beside a column of marginal notes; the notes drop below the prose on narrow screens. */
export function TextBlock({ children, notes }) {
  return (
    <div className="text-grid">
      <div className="prose">{children}</div>
      {notes && <div className="notes">{notes}</div>}
    </div>
  );
}

/** A marginal note beside the paragraph it annotates. */
export function Sidenote({ title, children }) {
  return (
    <aside className="sidenote">
      {title && <strong>{title}</strong>}
      {children}
    </aside>
  );
}

/** A number worth remembering, set large in the margin with what it counts. */
export function Keynote({ value, children }) {
  return (
    <div className="keynote">
      <div className="display">{value}</div>
      <div className="label">{children}</div>
    </div>
  );
}

/** A short list of headline figures under their descriptions. */
export function Facts({ items }) {
  return (
    <dl className="facts">
      {items.map(({ value, label }) => (
        <div key={label}>
          <dd>{value}</dd>
          <dt>{label}</dt>
        </div>
      ))}
    </dl>
  );
}

const TICK = "M2 7.2 5.4 10.6 12 3.6";
const CROSS = "M3.2 3.2 10.8 10.8M10.8 3.2 3.2 10.8";

/** Whether a pre-registered hypothesis was supported; the mark and the word both carry it, never colour alone. */
export function Outcome({ supported }) {
  return (
    <span className={`outcome ${supported ? "is-supported" : "is-unsupported"}`}>
      <svg viewBox="0 0 14 14" aria-hidden="true">
        <path
          d={supported ? TICK : CROSS}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {supported ? "supported" : "not supported"}
    </span>
  );
}

/** A disclosure holding the values behind a figure, closed by default, as in the README. */
export function More({ summary, children }) {
  return (
    <details className="more">
      <summary>{summary}</summary>
      {children}
    </details>
  );
}
