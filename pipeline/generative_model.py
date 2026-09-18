"""Fit a logistic generative model of cell-type wiring from distance, compartment, and class pairing."""

import json

import igraph as ig
import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import DATA, RESULTS, SEED
from pipeline.wiring_cost import edge_array, positions_array

NEGATIVES_PER_EDGE = 5
C_REGULARIZATION = 1.0
CV_FOLDS = 5
SAMPLE_SEED_OFFSET = 600_000
PREREGISTRATION_COMMIT = "e62c6df"
REPORT = RESULTS / "generative_model.md"
MODEL_JSON = RESULTS / "generative_model.json"
BLOCK = 64
MODELS = {
    "distance": ("distance",),
    "distance_compartment": ("distance", "compartment"),
    "G": ("distance", "compartment", "class_pair"),
    "G_deg": ("distance", "compartment", "class_pair", "degree"),
}


def logit_path(model: str):
    """Location of the full matrix of corrected edge log-odds for a generative model."""
    return DATA / f"generative_logit_{model}.npy"


def node_features(graph: ig.Graph) -> dict[str, np.ndarray]:
    """Per-node arrays used to build pair features: positions, compartment code, superclass code, log degrees."""
    compartment = np.asarray(graph.vs["compartment"], dtype=object)
    superclass = np.asarray(graph.vs["superclass"])
    classes = np.unique(superclass)
    return {
        "positions": positions_array(graph),
        "compartment": (compartment == "brain").astype(np.int8),
        "superclass": np.searchsorted(classes, superclass),
        "classes": classes,
        "log_out": np.log1p(np.asarray(graph.outdegree(), dtype=float)),
        "log_in": np.log1p(np.asarray(graph.indegree(), dtype=float)),
    }


def pair_design(sources: np.ndarray, targets: np.ndarray, nodes: dict, terms: tuple[str, ...]) -> sparse.csr_matrix:
    """Sparse design matrix for ordered pairs (sources[k], targets[k]).

    Columns, in order when the term is included: distance / 100 um and log(distance + 1 um); same-compartment
    indicator; one-hot (source superclass, target superclass); log(1 + out-degree of source) and
    log(1 + in-degree of target).
    """
    blocks = []
    if "distance" in terms:
        d = np.linalg.norm(nodes["positions"][sources] - nodes["positions"][targets], axis=1)
        blocks.append(sparse.csr_matrix(np.column_stack([d / 100.0, np.log(d + 1.0)])))
    if "compartment" in terms:
        same = (nodes["compartment"][sources] == nodes["compartment"][targets]).astype(float)
        blocks.append(sparse.csr_matrix(same[:, None]))
    if "class_pair" in terms:
        k = len(nodes["classes"])
        codes = nodes["superclass"][sources] * k + nodes["superclass"][targets]
        rows = np.arange(len(sources))
        blocks.append(sparse.csr_matrix((np.ones(len(sources)), (rows, codes)), shape=(len(sources), k * k)))
    if "degree" in terms:
        blocks.append(sparse.csr_matrix(np.column_stack([nodes["log_out"][sources], nodes["log_in"][targets]])))
    return sparse.hstack(blocks, format="csr")


def sample_non_edges(edges: np.ndarray, n: int, count: int, rng: np.random.Generator) -> np.ndarray:
    """``count`` distinct ordered pairs (i != j) drawn uniformly from pairs that are not edges."""
    edge_keys = edges[:, 0].astype(np.int64) * n + edges[:, 1]
    chosen = np.empty(0, dtype=np.int64)
    while len(chosen) < count:
        draw = int(1.3 * (count - len(chosen))) + 1000
        i, j = rng.integers(0, n, draw), rng.integers(0, n, draw)
        keys = i.astype(np.int64) * n + j
        keys = keys[(i != j) & ~np.isin(keys, edge_keys)]
        chosen = np.unique(np.concatenate([chosen, keys]))
    chosen = rng.choice(chosen, size=count, replace=False)
    return np.column_stack([chosen // n, chosen % n])


def log_likelihood(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, 1e-15, 1 - 1e-15)
    return float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def fit(x: sparse.csr_matrix, y: np.ndarray) -> LogisticRegression:
    model = LogisticRegression(C=C_REGULARIZATION, solver="lbfgs", max_iter=2000)
    return model.fit(x, y)


def fit_statistics(model: LogisticRegression, x: sparse.csr_matrix, y: np.ndarray) -> dict:
    """McFadden pseudo-R-squared, AIC, and in-sample log-likelihoods on the case-control sample."""
    ll = log_likelihood(y, model.predict_proba(x)[:, 1])
    ll_null = log_likelihood(y, np.full(len(y), y.mean()))
    k = x.shape[1] + 1
    return {"log_likelihood": ll, "log_likelihood_intercept_only": ll_null, "pseudo_r2_mcfadden": 1 - ll / ll_null,
            "aic": 2 * k - 2 * ll, "parameters": k, "iterations": int(model.n_iter_[0])}


def cross_validated_auc(x: sparse.csr_matrix, y: np.ndarray, seed: int) -> list[float]:
    folds = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=seed)
    return [float(roc_auc_score(y[test], fit(x[train], y[train]).predict_proba(x[test])[:, 1]))
            for train, test in folds.split(np.zeros(len(y)), y)]


def write_logits(model: LogisticRegression, nodes: dict, terms: tuple[str, ...], intercept_correction: float,
                 n: int, path) -> np.ndarray:
    """Corrected edge log-odds for every ordered pair as a float32 memory-mapped (n, n) array, diagonal -inf."""
    logits = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32, shape=(n, n))
    coef, intercept = model.coef_[0], model.intercept_[0] + intercept_correction
    targets_all = np.arange(n)
    for start in range(0, n, BLOCK):
        rows = np.arange(start, min(start + BLOCK, n))
        sources = np.repeat(rows, n)
        targets = np.tile(targets_all, len(rows))
        block = (pair_design(sources, targets, nodes, terms) @ coef + intercept).reshape(len(rows), n)
        block[np.arange(len(rows)), rows] = -np.inf
        logits[start:start + len(rows)] = block
    logits.flush()
    return logits


def logit_histogram(logits: np.ndarray, bin_width: float = 0.002) -> tuple[np.ndarray, np.ndarray]:
    """Counts of finite log-odds in bins of ``bin_width``, as (bin centres, counts)."""
    lo, hi = np.inf, -np.inf
    for start in range(0, logits.shape[0], 2048):
        block = logits[start:start + 2048]
        finite = block[np.isfinite(block)]
        lo, hi = min(lo, float(finite.min())), max(hi, float(finite.max()))
    edges = np.arange(np.floor(lo / bin_width) * bin_width, hi + 2 * bin_width, bin_width)
    counts = np.zeros(len(edges) - 1)
    for start in range(0, logits.shape[0], 2048):
        block = logits[start:start + 2048]
        counts += np.histogram(block[np.isfinite(block)], bins=edges)[0]
    return (edges[:-1] + edges[1:]) / 2, counts


def solve_shift(centres: np.ndarray, counts: np.ndarray, target_edges: float) -> float:
    """Scalar c such that the sum over pairs of sigmoid(logit + c) equals ``target_edges``."""
    lo, hi = -20.0, 20.0
    for _ in range(80):
        mid = (lo + hi) / 2
        expected = float(np.dot(counts, 1 / (1 + np.exp(-(centres + mid)))))
        lo, hi = (mid, hi) if expected < target_edges else (lo, mid)
    return (lo + hi) / 2


def main() -> None:
    graph = load_spatial_graph()
    n, edges = graph.vcount(), edge_array(graph)
    nodes = node_features(graph)
    rng = np.random.default_rng(SEED + SAMPLE_SEED_OFFSET)
    negatives = sample_non_edges(edges, n, NEGATIVES_PER_EDGE * len(edges), rng)
    pairs = np.vstack([edges, negatives])
    y = np.concatenate([np.ones(len(edges)), np.zeros(len(negatives))])
    total_non_edges = n * (n - 1) - len(edges)
    correction = float(np.log(len(negatives) / total_non_edges))

    results = {}
    for name, terms in MODELS.items():
        x = pair_design(pairs[:, 0], pairs[:, 1], nodes, terms)
        model = fit(x, y)
        stats_ = fit_statistics(model, x, y)
        stats_["cv_auc"] = cross_validated_auc(x, y, SEED)
        stats_["cv_auc_mean"] = float(np.mean(stats_["cv_auc"]))
        coefficients = {"distance_per_100um": float(model.coef_[0][0]), "log_distance": float(model.coef_[0][1])}
        column = 2
        if "compartment" in terms:
            coefficients["same_compartment"] = float(model.coef_[0][column])
            column += 1
        if "class_pair" in terms:
            k = len(nodes["classes"])
            block = model.coef_[0][column:column + k * k].reshape(k, k)
            coefficients["class_pair"] = {f"{a}->{b}": float(block[i, j]) for i, a in enumerate(nodes["classes"])
                                          for j, b in enumerate(nodes["classes"])}
            column += k * k
        if "degree" in terms:
            coefficients["log_out_degree_source"] = float(model.coef_[0][column])
            coefficients["log_in_degree_target"] = float(model.coef_[0][column + 1])
        stats_.update(intercept=float(model.intercept_[0]), intercept_corrected=float(model.intercept_[0] + correction),
                      coefficients=coefficients)
        if name in ("G", "G_deg"):
            logits = write_logits(model, nodes, terms, correction, n, logit_path(name))
            centres, counts = logit_histogram(logits)
            stats_["shift_to_match_edges"] = solve_shift(centres, counts, len(edges))
            stats_["expected_edges_before_shift"] = float(np.dot(counts, 1 / (1 + np.exp(-centres))))
            del logits
        results[name] = stats_
        print(f"{name}: pseudo-R2 {stats_['pseudo_r2_mcfadden']:.4f}, AIC {stats_['aic']:.0f}, "
              f"CV AUC {stats_['cv_auc_mean']:.4f}", flush=True)

    summary = {"preregistration_commit": PREREGISTRATION_COMMIT, "nodes": n, "edges": int(len(edges)),
               "negatives": int(len(negatives)), "all_non_edges": int(total_non_edges),
               "intercept_correction": correction, "superclasses": nodes["classes"].tolist(), "models": results}
    MODEL_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_report(summary)


def write_report(s: dict) -> None:
    text = REPORT.read_text(encoding="utf-8").split("\n## Fit")[0].rstrip() + "\n"
    m = s["models"]
    labels = {"distance": "distance only", "distance_compartment": "distance + compartment",
              "G": "distance + compartment + class pairing (G)", "G_deg": "G + source out-degree + target in-degree"}
    g = m["G"]["coefficients"]
    ranked = sorted(g["class_pair"].items(), key=lambda kv: kv[1], reverse=True)
    lines = [
        text,
        "## Fit",
        "",
        f"Protocol committed in `{s['preregistration_commit']}` before any model was fitted.",
        "",
        f"Fitting sample: all {s['edges']:,} edges and {s['negatives']:,} uniformly sampled non-edges, out of "
        f"{s['all_non_edges']:,} non-edge ordered pairs. Intercept correction for the sampling: "
        f"{s['intercept_correction']:.3f}.",
        "",
        "| model | parameters | McFadden pseudo-R² | AIC | 5-fold CV AUC (range over folds) |",
        "|---|---|---|---|---|",
        *[f"| {labels[k]} | {v['parameters']} | {v['pseudo_r2_mcfadden']:.4f} | {v['aic']:,.0f} | "
          f"{v['cv_auc_mean']:.4f} ({min(v['cv_auc']):.4f}–{max(v['cv_auc']):.4f}) |" for k, v in m.items()],
        "",
        f"Model G coefficients: {g['distance_per_100um']:.3f} per 100 µm of distance and {g['log_distance']:.3f} per unit "
        f"of log distance; same compartment {g['same_compartment']:.3f}. Largest class-pairing coefficients: "
        + ", ".join(f"`{k}` {v:.2f}" for k, v in ranked[:5]) + ". Smallest: "
        + ", ".join(f"`{k}` {v:.2f}" for k, v in ranked[-5:]) + ".",
        "",
        f"After the intercept correction, model G expects {m['G']['expected_edges_before_shift']:,.0f} edges over all "
        f"ordered pairs against {s['edges']:,} real edges; the shift that matches the count exactly is "
        f"{m['G']['shift_to_match_edges']:.3f} (model G+deg: expected {m['G_deg']['expected_edges_before_shift']:,.0f}, "
        f"shift {m['G_deg']['shift_to_match_edges']:.3f}).",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
