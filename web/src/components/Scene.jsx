import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { posterUrl, sceneUrl } from "../lib/data.js";
import { count, micron, millimetre } from "../lib/format.js";
import { useMedia, useNear, useReducedMotion } from "../lib/hooks.js";
import { Segmented } from "./ui.jsx";

const OVERLAYS = [
  { value: "length", label: "Length" },
  { value: "rich", label: "Rich partner" },
  { value: "value", label: "Flow carried" },
];

const READING = {
  length: "coloured by length, from dark red for the shortest to pale orange for about a millimetre",
  rich: "with connections to a well-connected partner picked out and the rest dimmed",
  value: "with each connection coloured by the sensory-to-motor flow its cell type carries",
};

const POSTER_ALT =
  "The male fly central nervous system seen from the front, brain above and nerve cord below, with every " +
  "connection that crosses the neck drawn as a line coloured by its length.";

function webglAvailable() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
  } catch (error) {
    return false;
  }
}

/** Fetch the packed scene, reporting the share of it that has arrived. */
async function fetchScene(onProgress) {
  const response = await fetch(sceneUrl);
  if (!response.ok) throw new Error(`the connective view could not be loaded (${response.status})`);
  const total = Number(response.headers.get("content-length")) || 0;
  if (!response.body) return response.json();
  const reader = response.body.getReader();
  const chunks = [];
  let read = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    read += value.length;
    // Compressed responses decode to more bytes than Content-Length promised, so the bar never runs past its end.
    if (total) onProgress(Math.min(0.99, read / total));
  }
  onProgress(1);
  const body = new Uint8Array(read);
  let at = 0;
  for (const chunk of chunks) {
    body.set(chunk, at);
    at += chunk.length;
  }
  return JSON.parse(new TextDecoder().decode(body));
}

/**
 * The connective view: the neuropil shell with every neck-crossing connection drawn through it. The still render
 * stands in until the scene has arrived, and stays for a reader without WebGL. On a small screen the scene is
 * loaded only when it is asked for, so a phone is not made to download it.
 */
export default function Scene({ nodes, neck }) {
  const holder = useRef(null);
  const viewer = useRef(null);
  const near = useNear(holder);
  const reducedMotion = useReducedMotion();
  const small = useMedia("(max-width: 700px)");
  const [wanted, setWanted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [live, setLive] = useState(false);
  const [failed, setFailed] = useState(null);
  const [mode, setMode] = useState("length");
  const [picked, setPicked] = useState("");

  const entries = useMemo(
    () => nodes.map((row, index) => ({ label: `${row.cell_type} ${row.side}`, index, row })),
    [nodes],
  );
  const byLabel = useMemo(() => new Map(entries.map((entry) => [entry.label.toLowerCase(), entry])), [entries]);
  const selected = byLabel.get(picked.trim().toLowerCase()) ?? null;

  const supported = useMemo(webglAvailable, []);
  const shouldLoad = near && supported && (wanted || !small);

  useEffect(() => {
    if (!shouldLoad || viewer.current || failed) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const [header, { createViewer }] = await Promise.all([
          fetchScene((value) => !cancelled && setProgress(value)),
          import("../lib/viewer.js"),
        ]);
        if (cancelled || !holder.current) return;
        viewer.current = createViewer(holder.current, header, nodes, { reducedMotion });
        setLive(true);
      } catch (error) {
        if (!cancelled) setFailed(error);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [shouldLoad, nodes, reducedMotion, failed]);

  useEffect(
    () => () => {
      viewer.current?.dispose();
      viewer.current = null;
    },
    [],
  );

  useEffect(() => {
    viewer.current?.setMode(mode);
  }, [mode, live]);

  useEffect(() => {
    viewer.current?.select(selected ? selected.index : null);
  }, [selected, live]);

  const clear = useCallback(() => setPicked(""), []);

  const label = live
    ? `Rotatable view of the fly central nervous system with all ${count(neck.edges)} connections that cross the neck, ${READING[mode]}.`
    : POSTER_ALT;

  return (
    <div className="hero-stage">
      <div className={`scene${live ? " is-live" : ""}`} ref={holder} role="img" aria-label={label}>
        <img className="scene-poster" src={posterUrl} alt="" width="1920" height="1080" />
        {shouldLoad && !live && !failed && (
          <p className="scene-status">
            <span className="scene-progress" aria-hidden="true">
              <span style={{ transform: `scaleX(${progress || 0.04})` }} />
            </span>
            Loading the connective
          </p>
        )}
        {failed && <p className="scene-status">Showing the still render: {failed.message}</p>}
      </div>

      <div className="scene-controls">
        <div className="scene-row">
          <Segmented label="Colour the connections by" options={OVERLAYS} value={mode} onChange={setMode} />
          {mode === "length" && (
            <div className="ramp-scale">
              <span className="ramp-bar" aria-hidden="true" />
              <span className="ramp-ticks" aria-hidden="true">
                <span>200</span>
                <span>1000</span>
              </span>
              <span className="ramp-title" aria-hidden="true">
                connection length (µm)
              </span>
              <span className="visually-hidden">Connection length, 200 to 1000 micrometres.</span>
            </div>
          )}
        </div>

        {!supported && <p className="scene-readout">This browser has no WebGL, so the still render is shown.</p>}
        {supported && small && !wanted && (
          <button type="button" className="btn" onClick={() => setWanted(true)}>
            Turn on the rotatable view (2 MB)
          </button>
        )}

        {live && (
          <>
            <div className="scene-pick">
              <input
                className="input"
                type="search"
                list="connective-types"
                placeholder="Show one cell type, such as DNg98 L"
                aria-label="Show one cell type"
                value={picked}
                onChange={(event) => setPicked(event.target.value)}
              />
              <button type="button" className="btn" onClick={clear} disabled={!picked}>
                Show all
              </button>
            </div>
            <datalist id="connective-types">
              {entries.map((entry) => (
                <option key={entry.label} value={entry.label} />
              ))}
            </datalist>
          </>
        )}

        <p className="scene-readout" aria-live="polite">
          {selected ? (
            <>
              <span className="id">{selected.row.cell_type}</span> {selected.row.side}, {selected.row.direction}:{" "}
              <span className="num">{count(selected.row.edges)}</span> neck-crossing connections,{" "}
              <span className="num">{millimetre(selected.row.price_um)}</span> of wire, carrying{" "}
              <span className="num">{count(selected.row.value)}</span> units of flow.
            </>
          ) : live ? (
            <>
              Drag to turn the view. All <span className="num">{count(neck.edges)}</span> neck-crossing connections,
              mean <span className="num">{micron(neck.mean_length_um)}</span>.
            </>
          ) : (
            "Every connection between a descending or ascending cell type and a partner on the far side of the neck."
          )}
        </p>
      </div>
    </div>
  );
}
