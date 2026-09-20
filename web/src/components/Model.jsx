import { useState } from "react";
import Generative, { FitTable, GenerativeTable } from "./figures/Generative.jsx";
import { Figure, HeadingLevel, Keynote, More, Segmented, Sidenote, TextBlock } from "./ui.jsx";
import { count, fixed, percent } from "../lib/format.js";

const MODELS = [
  { value: "G", label: "Model G" },
  { value: "G_deg", label: "Model G + degrees" },
];

export default function Model({ data }) {
  const [model, setModel] = useState("G");
  const comparison = data.generative.comparison.models[model];
  const properties = Object.values(comparison.properties);
  const reproduced = properties.filter((p) => p.reproduced).length;
  const routes = comparison.properties.rich_routes;
  const reciprocity = comparison.properties.reciprocity;

  return (
    <section className="section" id="model" aria-labelledby="model-title">
      <div className="wrap">
        <HeadingLevel level={3}>
          <div className="section-head">
            <h2 id="model-title">What distance and cell class already explain</h2>
            <p className="lede">
              If a model that knows only where cell types sit and what kind they are can produce the rich-to-rich
              routing, then that routing needs no further explanation.
            </p>
          </div>

          <TextBlock
            notes={[
              <Keynote key="reproduced" value={`${reproduced} of ${properties.length}`}>
                properties of the real graph reproduced by {model === "G" ? "model G" : "model G + degrees"}
              </Keynote>,
              <Sidenote key="fit" title="It is not a bad fit">
                Model G reaches a cross-validated AUC of {fixed(data.generative.fit.models.G.cv_auc_mean, 3)} at
                predicting which pairs are connected. Fitting well and reproducing structure are different things.
              </Sidenote>,
              <Sidenote key="independence" title="What it cannot do">
                Both models draw every pair independently, so neither can produce reciprocity or clustering. The real
                graph has {fixed(reciprocity.real / reciprocity.synthetic_mean, 0)} times the reciprocity of the
                synthetic ones.
              </Sidenote>,
            ]}
          >
            <p>
              Model G predicts each connection from the distance between two cell types, whether they share a
              compartment, and their pair of cell classes. It knows nothing of the real degrees. Model G + degrees
              adds them. Both are fitted on every connection and a sample of non-connections, then used to draw{" "}
              {data.generative.comparison.n_synthetic} synthetic graphs with the expected number of connections fixed
              to the real one.
            </p>
            <p>
              Model G reproduces {reproduced} of {properties.length} properties, and one of them is the number of
              rich-to-rich routes through the connective: {count(routes.synthetic_mean)} on average against{" "}
              {count(routes.real)} real. The route excess over degree-preserving rewiring therefore lies within what
              distance and cell class produce on their own. That is the most useful thing this section says, and it
              is a caution about the previous one.
            </p>
          </TextBlock>

          <Figure
            number={11}
            title="Distance, compartment and cell class reproduce the rich-to-rich routes, and little else"
            caption={
              <>
                Each property of the real graph as a multiple of the mean of {data.generative.comparison.n_synthetic}{" "}
                synthetic graphs, on a logarithmic axis. The pale band is the synthetic central 95%: a hollow point
                inside it is a property the model reproduces, a filled point outside it is one it misses. Hover a row
                for the values in their own units.
              </>
            }
            controls={<Segmented label="Wiring model" options={MODELS} value={model} onChange={setModel} />}
          >
            <Generative data={data} model={model} />
            <More summary="Values behind Figure 11">
              <GenerativeTable data={data} model={model} />
              <FitTable data={data} />
              <p className="caption">
                Model G + degrees reproduces{" "}
                {Object.values(data.generative.comparison.models.G_deg.properties).filter((p) => p.reproduced).length}{" "}
                of {properties.length}. Both models fix the expected number of connections to the real{" "}
                {count(data.generative.comparison.real_edges)} with a shift on the intercept, so the comparison is not
                about size. Earlier generative models of the fly brain combined distance with degree; adding degrees
                here raises the fit to a pseudo-R² of{" "}
                {fixed(data.generative.fit.models.G_deg.pseudo_r2_mcfadden, 3)} without reproducing more of the
                structure.
              </p>
            </More>
          </Figure>
        </HeadingLevel>
      </div>
    </section>
  );
}
