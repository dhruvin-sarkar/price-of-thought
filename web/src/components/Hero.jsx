import Scene from "./Scene.jsx";
import { reportUrl } from "../lib/data.js";
import { fixed, percent, times } from "../lib/format.js";
import { headline } from "../lib/headline.js";

export default function Hero({ data }) {
  const h = headline(data);

  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="wrap hero-grid">
        <div className="hero-copy">
          <h1 id="hero-title" className="hero-title">
            The Price of Thought
          </h1>
          <p className="hero-deck">
            Is a fly&rsquo;s nervous system wired to keep its connections short, and what do its longest wires buy?
          </p>
          <p className="hero-answer">
            Economically, but not optimally, and its most expensive wires buy no more than ordinary long ones. Cell
            types in the male <i>Drosophila</i> central nervous system sit where their connections use{" "}
            <strong>{fixed(h.ratio, 3)} times</strong> the wire of random placements of the same positions, yet simple
            swaps still cut at least <strong>{percent(h.swap)}</strong>.
          </p>
          <dl className="hero-stats">
            <div>
              <dd>{percent(h.neck.cost_share)}</dd>
              <dt>of all wire in the {percent(h.neck.edge_share)} of connections that cross the neck</dt>
            </div>
            <div>
              <dd>{times(h.flowRatio, 2)}</dd>
              <dt>the routing lost by cutting the neck, against random wiring of the same length</dt>
            </div>
          </dl>
          <p className="hero-links">
            <a className="btn is-strong" href="#placement">
              Read the findings
            </a>
            <a className="btn" href={reportUrl}>
              Technical report
            </a>
          </p>
        </div>
        <Scene nodes={data.price.nodes} neck={h.neck} />
      </div>
    </section>
  );
}
