# Generative wiring model

## Hypothesis and protocol (stated before any model was fitted)

**Data.** Every ordered pair (i, j), i ≠ j, of the 23,073 (cell type, hemisphere) nodes; the response is 1 when the edge i → j is in the graph.

**Model G (primary, as specified).** Logistic regression of edge presence on: distance between the two node positions (in units of 100 µm) and its logarithm, log(distance + 1 µm); an indicator that both nodes share a compartment; and a one-hot term for the ordered pair (source superclass, target superclass). Fitted with scikit-learn `LogisticRegression` (lbfgs, L2 penalty, C = 1.0, which keeps superclass pairs without any edge from diverging).

**Negative sampling.** All real edges plus 5 non-edges per real edge, drawn uniformly without replacement from all ordered non-edge pairs with a fixed seed. Case-control sampling changes only the intercept; the fitted intercept is corrected by log(sampled non-edges / all non-edges) before generating graphs.

**Fit quality.** McFadden pseudo-R² (1 − log-likelihood of the model / log-likelihood of an intercept-only model, on the fitting sample), AIC, and 5-fold cross-validated ROC AUC. Nested models are reported to show what each term adds: distance only; distance + compartment; model G. A secondary model G+deg adds log(1 + out-degree of i) and log(1 + in-degree of j).

**Synthetic graphs.** 50 graphs from model G, and 50 from model G+deg as a secondary. Each ordered pair is an independent Bernoulli draw with probability σ(corrected logit + c), where the scalar shift c is solved so that the expected number of edges equals the number of real edges; realized edge counts are reported.

**Compared properties** (each computed on the real graph and on every synthetic graph): standard deviation and maximum of in-degree and of out-degree; total wiring cost; median edge length; fraction of edges joining the two compartments; reciprocity; global transitivity of the undirected graph; sensory-to-motor flow capacity and reachable pairs (sets as in `results/connective_value.md`); number of neck-crossing edges; and the rich-to-rich route statistic R of `results/connective_richclub.md`. The Kolmogorov-Smirnov distance between real and synthetic in- and out-degree distributions is reported descriptively.

**Criterion.** A property counts as reproduced when the real value lies within the central 95% of the 50 synthetic values (2.5th to 97.5th percentile). The report states the fraction of properties reproduced and lists each one either way. No threshold for a "good" model is set; the model reproducing many or few properties is equally reportable.
