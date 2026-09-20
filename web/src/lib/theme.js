import { useCallback, useEffect, useState } from "react";

const KEY = "price-of-thought:theme";
const DARK = "(prefers-color-scheme: dark)";

function stored() {
  try {
    const value = localStorage.getItem(KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch (error) {
    return null;
  }
}

/**
 * The theme in force and a toggle for it. The inline script in index.html has already put the resolved theme on
 * the root element before first paint; this keeps it in step with the system setting until the reader chooses.
 */
export function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme ?? "light");
  const [chosen, setChosen] = useState(stored);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (chosen) return undefined;
    const query = window.matchMedia(DARK);
    const follow = () => setTheme(query.matches ? "dark" : "light");
    follow();
    query.addEventListener("change", follow);
    return () => query.removeEventListener("change", follow);
  }, [chosen]);

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(KEY, next);
      } catch (error) {
        /* storage blocked: the choice lasts for this page only */
      }
      setChosen(next);
      return next;
    });
  }, []);

  return [theme, toggle];
}
