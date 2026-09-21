import Anatomy from "./components/Anatomy.jsx";
import Budget from "./components/Budget.jsx";
import Buys from "./components/Buys.jsx";
import Connective from "./components/Connective.jsx";
import Hero from "./components/Hero.jsx";
import Methods, { Footer } from "./components/Methods.jsx";
import Model from "./components/Model.jsx";
import Nav from "./components/Nav.jsx";
import Placement from "./components/Placement.jsx";
import SectionBoundary from "./components/SectionBoundary.jsx";
import { reportUrl, useData } from "./lib/data.js";
import { useHashLanding } from "./lib/landing.js";

export default function App() {
  const { data, error } = useData("site.json");
  useHashLanding(Boolean(data));

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Nav ready={Boolean(data)} />
      <main id="main">
        {error && (
          <div className="wrap section">
            <p className="pending">
              The results could not be loaded ({error.message}). Reload the page; if the problem stays, the data
              files are missing from this build.
            </p>
          </div>
        )}
        {!error && !data && <HeroSkeleton />}
        {data && (
          <>
            <SectionBoundary>
              <Hero data={data} />
            </SectionBoundary>
            <SectionBoundary id="placement">
              <Placement data={data} />
            </SectionBoundary>
            <SectionBoundary id="budget">
              <Budget data={data} />
            </SectionBoundary>
            <SectionBoundary id="connective">
              <Connective data={data} />
            </SectionBoundary>
            <SectionBoundary id="model">
              <Model data={data} />
            </SectionBoundary>
            <SectionBoundary id="buys">
              <Buys data={data} />
            </SectionBoundary>
            <SectionBoundary id="anatomy">
              <Anatomy data={data} />
            </SectionBoundary>
            <SectionBoundary id="methods">
              <Methods data={data} />
            </SectionBoundary>
          </>
        )}
      </main>
      {data && (
        <SectionBoundary>
          <Footer data={data} />
        </SectionBoundary>
      )}
    </>
  );
}

/**
 * The hero before the results arrive: the same grid, the same stage, the same length scale, and the caption that
 * says what the stage will hold. Every box it draws is one the loaded hero also draws, so nothing moves when the
 * numbers land in it.
 */
function HeroSkeleton() {
  return (
    <section className="hero" aria-busy="true">
      <div className="wrap hero-grid">
        <div className="hero-copy">
          <h1 className="hero-title">The Price of Thought</h1>
          <p className="hero-deck">
            Is a fly&rsquo;s nervous system wired to keep its connections short, and what do its longest wires buy?
          </p>
          <p className="hero-answer">
            Loading the wiring economy of the male <i>Drosophila</i> central nervous system: where its cell types
            sit, what the connections between them cost, and what the ones that cross the neck buy.
          </p>
          <p className="hero-links">
            <a className="btn is-strong" href="#placement">
              Read the findings
            </a>
            <a className="btn" href={reportUrl}>
              Technical report
            </a>
          </p>
        </div>
        <div className="hero-stage">
          <div className="scene">
            <p className="scene-waiting">
              The male fly central nervous system seen from the front, brain above and nerve cord below, with every
              connection that crosses the neck drawn as a line coloured by its length.
            </p>
          </div>
          <div className="scene-controls">
            <div className="scene-row">
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
            </div>
            <p className="scene-readout">
              Every connection between a descending or ascending cell type and a partner on the far side of the
              neck.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
