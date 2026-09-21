import { useRef, useState } from "react";

const STEPS = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 };

/**
 * One tab stop for a list of rows. Arrow keys move between rows, Home and End jump to the ends, and focusing a
 * row makes it the active one, so its readout appears as it does under the pointer. Returns a function giving
 * the props to spread on the element holding one row. `className` names the class the focus style hangs on.
 */
export function useRovingRows(keys, onActive, className = "row-mark") {
  const refs = useRef(new Map());
  const [stop, setStop] = useState(null);
  const current = keys.includes(stop) ? stop : keys[0];

  return (key) => ({
    ref: (el) => {
      if (el) refs.current.set(key, el);
      else refs.current.delete(key);
    },
    className,
    tabIndex: key === current ? 0 : -1,
    onFocus: () => {
      setStop(key);
      onActive(key);
    },
    onBlur: () => onActive(null),
    onKeyDown: (event) => {
      const i = keys.indexOf(key);
      let next = null;
      if (event.key in STEPS) next = Math.max(0, Math.min(keys.length - 1, i + STEPS[event.key]));
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = keys.length - 1;
      if (next == null) return;
      event.preventDefault();
      setStop(keys[next]);
      refs.current.get(keys[next])?.focus();
    },
  });
}
