import Connective from "./components/Connective.jsx";
import Hero from "./components/Hero.jsx";
import Methods, { Footer } from "./components/Methods.jsx";
import Model from "./components/Model.jsx";
import Nav from "./components/Nav.jsx";
import Placement from "./components/Placement.jsx";
import SectionBoundary from "./components/SectionBoundary.jsx";
import { posterUrl, useData } from "./lib/data.js";

export default function App() {
  const { data, error } = useData("site.json");

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
            <SectionBoundary id="connective">
              <Connective data={data} />
            </SectionBoundary>
            <SectionBoundary id="model">
              <Model data={data} />
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

/** The hero with the still render in place, holding its layout while the results load. */
function HeroSkeleton() {
  return (
    <section className="hero" aria-busy="true">
      <div className="wrap hero-grid">
        <div className="hero-copy">
          <h1 className="hero-title">The Price of Thought</h1>
          <p className="hero-deck">
            Is a fly&rsquo;s nervous system wired to keep its connections short, and what do its longest wires buy?
          </p>
          <p className="hero-answer">Loading the wiring economy of the male Drosophila central nervous system.</p>
        </div>
        <div className="hero-stage">
          <div className="scene">
            <img className="scene-poster" src={posterUrl} alt="" width="1920" height="1080" />
          </div>
        </div>
      </div>
    </section>
  );
}
