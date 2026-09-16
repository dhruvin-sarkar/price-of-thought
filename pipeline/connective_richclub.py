"""Test whether routes through the brain-nerve cord connective preferentially join high-degree cell types."""

import argparse
import json
from multiprocessing import Pool

import igraph as ig
import numpy as np
import pandas as pd
from scipy import stats

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, SEED
from pipeline.figures import CONNECTIVE, MUTED, NULL, REAL, apply_style, plt
from pipeline.rewiring import rewire
from pipeline.wiring_cost import edge_array

N_NULLS = 1000
N_GRAPH_NULLS = 100
TOP_FRACTION = 0.10
THRESHOLDS = (0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50)
ALPHA = 0.05
NULL_SEED_OFFSET = 400_000
GRAPH_NULL_SEED_OFFSET = 450_000
PREREGISTRATION_COMMIT = "e62c6df"
REPORT = RESULTS / "connective_richclub.md"


def node_sets(graph: ig.Graph) -> dict[str, np.ndarray]:
    """Boolean vertex masks: descending and ascending connective nodes, and brain and nerve-cord partners."""
    role = np.asarray(graph.vs["connective"])
    compartment = np.asarray(graph.vs["compartment"], dtype=object)
    connective = role != "none"
    return {
        "descending": role == "descending",
        "ascending": role == "ascending",
        "connective": connective,
        "brain": ~connective & (compartment == "brain"),
        "vnc": ~connective & (compartment == "vnc"),
    }


def layer_edges(edges: np.ndarray, sets: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Split an (m, 2) edge array into the four connective layers B->DN, DN->V, V->AN, AN->B."""
    s, t = edges[:, 0], edges[:, 1]
    masks = {
        "D_in": sets["brain"][s] & sets["descending"][t],
        "D_out": sets["descending"][s] & sets["vnc"][t],
        "A_in": sets["vnc"][s] & sets["ascending"][t],
        "A_out": sets["ascending"][s] & sets["brain"][t],
    }
    return {name: edges[mask] for name, mask in masks.items()}


def partner_richness(edges: np.ndarray, connective: np.ndarray) -> np.ndarray:
    """Total degree of every vertex in the subgraph induced on non-connective vertices (0 for connective ones)."""
    n = len(connective)
    kept = edges[~connective[edges[:, 0]] & ~connective[edges[:, 1]]]
    return np.bincount(kept[:, 0], minlength=n) + np.bincount(kept[:, 1], minlength=n)


def rich_mask(richness: np.ndarray, members: np.ndarray, top_fraction: float) -> np.ndarray:
    """Members whose richness is at or above the (1 - top_fraction) quantile of richness among members."""
    threshold = np.quantile(richness[members], 1 - top_fraction)
    return members & (richness >= threshold)


def route_counts(layers: dict[str, np.ndarray], rich_brain: np.ndarray, rich_vnc: np.ndarray) -> dict[str, int]:
    """Number of rich-to-rich two-edge routes through descending and through ascending connective nodes."""
    n = len(rich_brain)
    d_in = np.bincount(layers["D_in"][rich_brain[layers["D_in"][:, 0]], 1], minlength=n)
    d_out = np.bincount(layers["D_out"][rich_vnc[layers["D_out"][:, 1]], 0], minlength=n)
    a_in = np.bincount(layers["A_in"][rich_vnc[layers["A_in"][:, 0]], 1], minlength=n)
    a_out = np.bincount(layers["A_out"][rich_brain[layers["A_out"][:, 1]], 0], minlength=n)
    descending, ascending = int(np.dot(d_in, d_out)), int(np.dot(a_in, a_out))
    return {"descending": descending, "ascending": ascending, "total": descending + ascending}


def randomize_layer(layer: np.ndarray, n_vertices: int, seed: int) -> np.ndarray:
    """Degree-preserving randomization of one layer's edges with the Fault Lines rewiring function."""
    graph = ig.Graph(n=n_vertices, edges=layer.tolist(), directed=True)
    graph.es["weight"] = [1] * graph.ecount()
    return np.asarray(rewire(graph, seed).get_edgelist(), dtype=np.int64).reshape(-1, 2)


def rich_edge_fraction(layers: dict[str, np.ndarray], rich_brain: np.ndarray, rich_vnc: np.ndarray) -> float:
    """Fraction of layer edges whose partner (non-connective) endpoint is rich."""
    hits = (
        rich_brain[layers["D_in"][:, 0]].sum() + rich_vnc[layers["D_out"][:, 1]].sum()
        + rich_vnc[layers["A_in"][:, 0]].sum() + rich_brain[layers["A_out"][:, 1]].sum()
    )
    return float(hits / sum(len(layer) for layer in layers.values()))


def enrichment_null(
    layers: dict[str, np.ndarray], sets: dict[str, np.ndarray], rich_brain: np.ndarray, rich_vnc: np.ndarray,
    n_nulls: int, seed: int,
) -> np.ndarray:
    """Rich-partner edge fraction when each connective node's partners are redrawn uniformly without replacement.

    The number of rich partners among k partners drawn without replacement from N eligible partners, K of them
    rich, is hypergeometric, so each connective node's draw is sampled directly.
    """
    rng = np.random.default_rng(seed)
    n = len(rich_brain)
    groups = {"D_in": (1, "brain", rich_brain), "D_out": (0, "vnc", rich_vnc),
              "A_in": (1, "vnc", rich_vnc), "A_out": (0, "brain", rich_brain)}
    total_edges = sum(len(layer) for layer in layers.values())
    hits = np.zeros(n_nulls)
    for name, (connective_column, partner_set, rich) in groups.items():
        degrees = np.bincount(layers[name][:, connective_column], minlength=n)
        degrees = degrees[degrees > 0]
        eligible, n_rich = int(sets[partner_set].sum()), int(rich.sum())
        draws = rng.hypergeometric(n_rich, eligible - n_rich, np.tile(degrees, (n_nulls, 1)))
        hits += draws.sum(axis=1)
    return hits / total_edges


def rich_club_coefficient(edges: np.ndarray, n_vertices: int) -> tuple[np.ndarray, np.ndarray]:
    """Directed rich-club coefficient phi(k) = E(>k) / (N(>k) (N(>k) - 1)) for k = 0 .. max total degree.

    Returns:
        (phi, n_above): arrays indexed by k; phi is NaN where fewer than two vertices have degree above k.
    """
    degree = np.bincount(edges[:, 0], minlength=n_vertices) + np.bincount(edges[:, 1], minlength=n_vertices)
    k_max = int(degree.max())
    n_at = np.bincount(degree, minlength=k_max + 1)
    n_above = n_at[::-1].cumsum()[::-1] - n_at
    edge_min = np.minimum(degree[edges[:, 0]], degree[edges[:, 1]])
    e_at = np.bincount(edge_min, minlength=k_max + 1)
    e_above = e_at[::-1].cumsum()[::-1] - e_at
    with np.errstate(divide="ignore", invalid="ignore"):
        phi = np.where(n_above >= 2, e_above / (n_above * (n_above - 1.0)), np.nan)
    return phi, n_above


def upper_p(real: float, null: np.ndarray) -> float:
    """One-sided permutation p-value for real > null, with the +1 correction."""
    return float((1 + np.sum(np.asarray(null) >= real)) / (1 + len(null)))


def compare(real: float, null: np.ndarray) -> dict:
    """One-sided (real > null) comparison of a real statistic with its null distribution."""
    null = np.asarray(null, dtype=float)
    sd = float(np.std(null, ddof=1))
    p = upper_p(real, null)
    return {
        "real": float(real), "null_mean": float(null.mean()), "null_sd": sd,
        "null_min": float(null.min()), "null_max": float(null.max()),
        "n_at_or_above_real": int(np.sum(null >= real)), "ratio": float(real / null.mean()),
        "z_score": float((real - null.mean()) / sd) if sd > 0 else float("nan"),
        "p_value": p, "significant": p < ALPHA,
    }


_WORKER: dict = {}


def _init_route_worker(layers, n_vertices, rich_sets) -> None:
    _WORKER.update(layers=layers, n_vertices=n_vertices, rich_sets=rich_sets)


def _route_null_job(index: int) -> dict:
    seed = SEED + NULL_SEED_OFFSET + 10 * index
    randomized = {name: randomize_layer(layer, _WORKER["n_vertices"], seed + i)
                  for i, (name, layer) in enumerate(_WORKER["layers"].items())}
    return {fraction: route_counts(randomized, rb, rv) for fraction, (rb, rv) in _WORKER["rich_sets"].items()}


def _init_graph_worker(graph) -> None:
    _WORKER.update(graph=graph)


def _graph_null_job(index: int) -> np.ndarray:
    graph = _WORKER["graph"]
    null = rewire(graph, SEED + GRAPH_NULL_SEED_OFFSET + index)
    return rich_club_coefficient(edge_array(null), graph.vcount())[0]


def plot(route: dict, nulls: pd.DataFrame, curve: pd.DataFrame, club: dict) -> None:
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), dpi=200)
    ax = axes[0]
    for key, color, label in (("descending", CONNECTIVE, "descending routes"), ("ascending", NULL, "ascending routes")):
        values = nulls[f"{key}_{TOP_FRACTION}"]
        ax.hist(values, bins=40, color=color, alpha=0.5, edgecolor="none", label=f"{label}, randomized")
        ax.axvline(route[key]["real"], color=color, linewidth=2)
    ax.set_title("Rich-to-rich routes, top 10% partners", loc="left")
    ax.set_xlabel("routes (vertical lines: real graph)")
    ax.set_ylabel("randomizations")
    ax.legend(loc="upper right", fontsize=7.5)

    ax = axes[1]
    ax.fill_between(100 * curve["top_fraction"], curve["ratio_lo"], curve["ratio_hi"], color=NULL, alpha=0.25,
                    linewidth=0, label="randomized, central 95%")
    ax.plot(100 * curve["top_fraction"], curve["ratio"], color=REAL, marker="o", label="real / randomized mean")
    ax.axhline(1, color=MUTED, linewidth=1, linestyle="--")
    ax.set_xscale("log")
    ax.set_xticks([1, 2, 5, 10, 20, 50], ["1", "2", "5", "10", "20", "50"])
    ax.set_title("All routes, by richness threshold", loc="left")
    ax.set_xlabel("partners counted as rich (top %)")
    ax.set_ylabel("routes relative to randomized mean")
    ax.legend(loc="upper right", fontsize=7.5)

    ax = axes[2]
    k = np.asarray(club["k"])
    ax.fill_between(k, club["null_norm_lo"], club["null_norm_hi"], color=NULL, alpha=0.25, linewidth=0,
                    label="randomized graphs, range")
    ax.plot(k, club["phi_norm"], color=REAL, linewidth=1.6, label="real graph")
    ax.axhline(1, color=MUTED, linewidth=1, linestyle="--")
    ax.set_title("Whole-CNS rich club", loc="left")
    ax.set_xlabel("total degree k")
    ax.set_ylabel("normalized rich-club coefficient")
    ax.legend(loc="upper left", fontsize=7.5)
    fig.text(0.01, 0.01, "Randomizations preserve every node's degree within each connective layer (left, middle) or "
             "in the whole graph (right).", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(RESULTS / "connective_richclub.png")
    plt.close(fig)


def hypothesis_section() -> str:
    return REPORT.read_text(encoding="utf-8").split("\n## Procedure")[0].rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-nulls", type=int, default=N_NULLS)
    parser.add_argument("--n-graph-nulls", type=int, default=N_GRAPH_NULLS)
    parser.add_argument("--workers", type=int, default=15)
    parser.add_argument("--report-only", action="store_true", help="rewrite the report from the saved JSON")
    args = parser.parse_args()
    if args.report_only:
        summary = json.loads((RESULTS / "connective_richclub.json").read_text(encoding="utf-8"))
        if "degree_counts" not in summary:
            summary["degree_counts"] = load_spatial_graph().degree(mode="all")
            (RESULTS / "connective_richclub.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        write_report(summary, pd.DataFrame(summary["threshold_curve"]))
        return

    graph = load_spatial_graph()
    n = graph.vcount()
    edges = edge_array(graph)
    sets = node_sets(graph)
    layers = layer_edges(edges, sets)
    richness = partner_richness(edges, sets["connective"])
    rich_sets = {f: (rich_mask(richness, sets["brain"], f), rich_mask(richness, sets["vnc"], f)) for f in THRESHOLDS}
    real = {f: route_counts(layers, *rich_sets[f]) for f in THRESHOLDS}

    with Pool(args.workers, initializer=_init_route_worker, initargs=(layers, n, rich_sets)) as pool:
        results = pool.map(_route_null_job, range(args.n_nulls), chunksize=8)
    nulls = pd.DataFrame(
        [{f"{key}_{f}": r[f][key] for f in THRESHOLDS for key in ("descending", "ascending", "total")} for r in results]
    )
    nulls.to_csv(RESULTS / "connective_richclub_nulls.csv", index_label="randomization")
    print("route nulls done", flush=True)

    route = {key: compare(real[TOP_FRACTION][key], nulls[f"{key}_{TOP_FRACTION}"].to_numpy())
             for key in ("total", "descending", "ascending")}
    curve_rows = []
    for f in THRESHOLDS:
        values = nulls[f"total_{f}"].to_numpy()
        c = compare(real[f]["total"], values)
        curve_rows.append({
            "top_fraction": f, "rich_brain": int(rich_sets[f][0].sum()), "rich_vnc": int(rich_sets[f][1].sum()),
            "real": c["real"], "null_mean": c["null_mean"], "ratio": c["ratio"], "z_score": c["z_score"],
            "p_value": c["p_value"], "ratio_lo": float(np.percentile(values, 2.5) / c["null_mean"]),
            "ratio_hi": float(np.percentile(values, 97.5) / c["null_mean"]),
        })
    curve = pd.DataFrame(curve_rows)

    rich_brain, rich_vnc = rich_sets[TOP_FRACTION]
    enrichment = compare(rich_edge_fraction(layers, rich_brain, rich_vnc),
                         enrichment_null(layers, sets, rich_brain, rich_vnc, args.n_nulls, SEED + NULL_SEED_OFFSET + 7))

    phi_real, n_above = rich_club_coefficient(edges, n)
    with Pool(args.workers, initializer=_init_graph_worker, initargs=(graph,)) as pool:
        phi_nulls = pool.map(_graph_null_job, range(args.n_graph_nulls), chunksize=1)
    print("graph nulls done", flush=True)
    k_len = len(phi_real)
    phi_nulls = np.array([np.pad(p, (0, max(0, k_len - len(p))), constant_values=np.nan)[:k_len] for p in phi_nulls])
    with np.errstate(invalid="ignore"):
        null_mean = np.nanmean(phi_nulls, axis=0)
        phi_norm = phi_real / null_mean
        exceeds = np.all(phi_real[None, :] > phi_nulls, axis=0) & np.isfinite(phi_real)
    regime = np.flatnonzero(exceeds)
    k_star = int(regime.min()) if len(regime) else None

    degree = np.asarray(graph.degree(mode="all"))
    connective = sets["connective"]
    high = degree >= np.quantile(degree, 0.9)
    table = [[int((high & connective).sum()), int((~high & connective).sum())],
             [int((high & ~connective).sum()), int((~high & ~connective).sum())]]
    odds, fisher_p = stats.fisher_exact(table, alternative="greater")
    membership = {"degree_threshold": float(np.quantile(degree, 0.9)), "table": table, "odds_ratio": float(odds),
                  "p_value": float(fisher_p), "significant": bool(fisher_p < ALPHA)}
    for role in ("descending", "ascending"):
        membership[f"{role}_share_high"] = float((high & sets[role]).sum() / sets[role].sum())
    membership["other_share_high"] = float((high & ~connective).sum() / (~connective).sum())
    if k_star is not None:
        above = degree > k_star
        membership["k_star"] = k_star
        membership["nodes_above_k_star"] = int(above.sum())
        for role in ("descending", "ascending"):
            membership[f"{role}_share_above_k_star"] = float((above & sets[role]).sum() / sets[role].sum())
        membership["other_share_above_k_star"] = float((above & ~connective).sum() / (~connective).sum())
        membership["connective_share_of_club"] = float((above & connective).sum() / above.sum())

    valid = np.isfinite(phi_norm) & (n_above >= 10)
    club = {"k": np.flatnonzero(valid).tolist(), "phi_norm": phi_norm[valid].tolist(),
            "null_norm_lo": (np.nanmin(phi_nulls, axis=0) / null_mean)[valid].tolist(),
            "null_norm_hi": (np.nanmax(phi_nulls, axis=0) / null_mean)[valid].tolist()}
    plot(route, nulls, curve, club)

    summary = {
        "preregistration_commit": PREREGISTRATION_COMMIT, "n_nulls": args.n_nulls, "n_graph_nulls": args.n_graph_nulls,
        "layer_edges": {name: int(len(layer)) for name, layer in layers.items()},
        "partners": {"brain": int(sets["brain"].sum()), "vnc": int(sets["vnc"].sum())},
        "connective_nodes": {"descending": int(sets["descending"].sum()), "ascending": int(sets["ascending"].sum())},
        "rich_threshold_richness": {"brain": float(np.quantile(richness[sets["brain"]], 0.9)),
                                    "vnc": float(np.quantile(richness[sets["vnc"]], 0.9))},
        "routes_top10": route, "threshold_curve": curve.to_dict(orient="records"),
        "endpoint_enrichment": enrichment, "whole_cns_membership": membership,
        "rich_club_regime_k": regime.tolist(),
        "phi_norm_at": {str(k): float(phi_norm[k]) for k in (10, 20, 40, 60, 80, 100, 150, 200) if k < k_len},
        "rich_club_curve": club,
        "degree_counts": degree.tolist(),
    }
    (RESULTS / "connective_richclub.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_report(summary, curve)
    print(json.dumps({k: summary[k] for k in ("routes_top10", "endpoint_enrichment", "whole_cns_membership")}, indent=1))


def write_report(s: dict, curve: pd.DataFrame) -> None:
    r, e, m = s["routes_top10"], s["endpoint_enrichment"], s["whole_cns_membership"]

    def verdict(result: dict) -> str:
        return "supported" if result["significant"] else "not supported"

    def row(label: str, c: dict) -> str:
        return (f"| {label} | {c['real']:,.0f} | {c['null_mean']:,.0f} ± {c['null_sd']:,.0f} | "
                f"{c['n_at_or_above_real']} / {s['n_nulls']} | {c['ratio']:.3f} | {c['z_score']:.1f} | "
                f"{c['p_value']:.4f} |")

    lines = [
        hypothesis_section(),
        "## Procedure",
        "",
        f"Hypotheses committed in `{PREREGISTRATION_COMMIT}` before any statistic in this file was computed.",
        "",
        f"- Connective nodes: {s['connective_nodes']['descending']:,} descending, {s['connective_nodes']['ascending']:,} "
        f"ascending. Partners: {s['partners']['brain']:,} brain, {s['partners']['vnc']:,} nerve cord.",
        "- Layer edges: " + ", ".join(f"{k} {v:,}" for k, v in s["layer_edges"].items()) + ".",
        f"- Rich partners (top 10%): richness at or above {s['rich_threshold_richness']['brain']:.0f} in the brain and "
        f"{s['rich_threshold_richness']['vnc']:.0f} in the nerve cord.",
        f"- {s['n_nulls']} layer randomizations; {s['n_graph_nulls']} whole-graph randomizations for the rich-club "
        "coefficient.",
        "",
        "## Result: rich-to-rich routes (H1)",
        "",
        "| routes | real | randomized mean ± sd | randomized ≥ real | real / randomized | z | p |",
        "|---|---|---|---|---|---|---|",
        row("all (primary)", r["total"]),
        row("descending", r["descending"]),
        row("ascending", r["ascending"]),
        "",
        f"**H1 is {verdict(r['total'])}.** Real rich-to-rich routes: {r['total']['ratio']:.3f} times the randomized "
        f"mean (z = {r['total']['z_score']:.1f}, p = {r['total']['p_value']:.4f}).",
        "",
        "### By richness threshold",
        "",
        "| top % of partners counted as rich | rich brain | rich nerve cord | real routes | randomized mean | "
        "real / randomized | z | p |",
        "|---|---|---|---|---|---|---|---|",
        *[f"| {100 * c.top_fraction:g} | {c.rich_brain:,} | {c.rich_vnc:,} | {c.real:,.0f} | {c.null_mean:,.0f} | "
          f"{c.ratio:.3f} | {c.z_score:.1f} | {c.p_value:.4f} |" for c in curve.itertuples()],
        "",
        "## Result: rich partners among connective partners (H2)",
        "",
        f"{100 * e['real']:.1f}% of connective layer edges have a rich partner, against {100 * e['null_mean']:.1f}% "
        f"± {100 * e['null_sd']:.1f}% when each connective node's partners are redrawn uniformly "
        f"(ratio {e['ratio']:.2f}, z = {e['z_score']:.1f}, p = {e['p_value']:.4f}). **H2 is {verdict(e)}.**",
        "",
        "## Result: descending and ascending neurons in the whole-CNS rich club (H3)",
        "",
        f"Nodes with total degree at or above the 90th percentile ({m['degree_threshold']:.0f}): "
        f"{100 * m['descending_share_high']:.1f}% of descending nodes, {100 * m['ascending_share_high']:.1f}% of "
        f"ascending nodes, {100 * m['other_share_high']:.1f}% of all other nodes. One-sided Fisher exact test: odds "
        f"ratio {m['odds_ratio']:.2f}, p = {m['p_value']:.3g}. **H3 is {verdict(m)}.**",
        "",
    ]
    if "k_star" in m:
        lines += [
            f"The lowest total degree at which the real rich-club coefficient exceeds all {s['n_graph_nulls']} "
            f"randomized graphs is k = {m['k_star']} (every such k is listed in `connective_richclub.json`). "
            f"{m['nodes_above_k_star']:,} nodes have degree above k = {m['k_star']}: "
            f"{100 * m['descending_share_above_k_star']:.1f}% of descending nodes, "
            f"{100 * m['ascending_share_above_k_star']:.1f}% of ascending nodes and "
            f"{100 * m['other_share_above_k_star']:.1f}% of other nodes; connective nodes make up "
            f"{100 * m['connective_share_of_club']:.1f}% of that set.",
            "",
        ]
    else:
        lines += [f"The real rich-club coefficient does not exceed all {s['n_graph_nulls']} randomized graphs at any "
                  "degree.", ""]
    club = s["rich_club_curve"]
    k_values, norm = np.asarray(club["k"]), np.asarray(club["phi_norm"])
    crossings = []
    for level in (1.1, 1.5, 2.0):
        reached = k_values[norm >= level]
        if len(reached):
            k = int(reached.min())
            crossings.append(f"{level:g} from k = {k} ({int(np.sum(np.asarray(s['degree_counts']) > k)):,} nodes above)")
    lines += ["Normalized rich-club coefficient at selected degrees: "
              + ", ".join(f"k = {k}: {v:.2f}" for k, v in s["phi_norm_at"].items()) + ".", "",
              "Descriptively, because exceedance of every randomized graph already holds where the excess is negligible, "
              "the normalized coefficient first reaches " + "; ".join(crossings) + ".", "",
              "![Connective rich club](connective_richclub.png)", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
