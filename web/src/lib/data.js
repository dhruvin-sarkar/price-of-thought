import { useEffect, useState } from "react";

const base = import.meta.env.BASE_URL;
const cache = new Map();

function load(name) {
  if (!cache.has(name)) {
    cache.set(
      name,
      fetch(`${base}data/${name}`).then((response) => {
        if (!response.ok) throw new Error(`${name} could not be loaded (${response.status})`);
        return response.json();
      }),
    );
  }
  return cache.get(name);
}

/** Load one exported JSON file. Values are never invented while it is missing: `data` stays null. */
export function useData(name) {
  const [state, setState] = useState({ data: null, error: null });
  useEffect(() => {
    if (!name) return undefined;
    let live = true;
    load(name)
      .then((data) => live && setState({ data, error: null }))
      .catch((error) => live && setState({ data: null, error }));
    return () => {
      live = false;
    };
  }, [name]);
  return state;
}

export const repoUrl = "https://github.com/dhruvin-sarkar/price-of-thought";
export const blobUrl = (path) => `${repoUrl}/blob/main/${path}`;

/** The technical report, published beside the site by the build. */
export const reportUrl = `${base}report.pdf`;

/** The still of the connective view, shown until the scene is ready and to anyone without WebGL. */

export const sceneUrl = `${base}data/scene.json`;
