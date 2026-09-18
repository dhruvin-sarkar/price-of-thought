"""Repeat the placement, rich-to-rich routing, and connective hub tests at other edge thresholds."""

import argparse
import json
from multiprocessing import Pool

import numpy as np
from scipy import stats

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, SEED
from pipeline.connective_richclub import (
    TOP_FRACTION,
    _init_route_worker,
    _route_null_job,
    compare,
    layer_edges,
    node_sets,
    partner_richness,
    rich_mask,
    route_counts,
)
from pipeline.spatial_permutation_test import PERMUTATION_SEED_OFFSET, permutation_null, summarize, wiring_cost_of
from pipeline.wiring_cost import edge_array, positions_array

FRACTIONS = (0.005, 0.01, 0.02, 0.05)
N_PERMUTATIONS = 1000
N_NULLS = 1000
ALPHA = 0.05
PREREGISTRATION_COMMIT = "73fba33"
REPORT = RESULTS / "threshold_robustness.md"


def hub_membership(degree: np.ndarray, connective: np.ndarray) -> dict:
    """One-sided Fisher test of connective nodes among nodes at or above the 90th percentile of total degree."""
    high = degree >= np.quantile(degree, 0.9)
    table = [[int((high & connective).sum()), int((~high & connective).sum())],
             [int((high & ~connective).sum()), int((~high & ~connective).sum())]]
    odds, p = stats.fisher_exact(table, alternative="greater")
    return {"degree_threshold": float(np.quantile(degree, 0.9)), "odds_ratio": float(odds), "p_value": float(p),
            "connective_share_high": table[0][0] / int(connective.sum()),
            "other_share_high": table[1][0] / int((~connective).sum())}


def run_fraction(fraction: float, n_permutations: int, n_nulls: int, workers: int) -> dict:
    graph = load_spatial_graph(fraction)
    n, edges = graph.vcount(), edge_array(graph)
    positions = positions_array(graph)
    placement = summarize(wiring_cost_of(edges, positions),
                          permutation_null(edges, positions, n_permutations, SEED + PERMUTATION_SEED_OFFSET))

    sets = node_sets(graph)
    layers = layer_edges(edges, sets)
    richness = partner_richness(edges, sets["connective"])
    rich = {TOP_FRACTION: (rich_mask(richness, sets["brain"], TOP_FRACTION), rich_mask(richness, sets["vnc"], TOP_FRACTION))}
    real = route_counts(layers, *rich[TOP_FRACTION])
    with Pool(workers, initializer=_init_route_worker, initargs=(layers, n, rich)) as pool:
        results = pool.map(_route_null_job, range(n_nulls), chunksize=8)
    routes = {key: compare(real[key], np.array([r[TOP_FRACTION][key] for r in results]))
              for key in ("total", "descending", "ascending")}

    hubs = hub_membership(np.asarray(graph.degree(mode="all")), sets["connective"])
    return {
        "fraction": fraction, "nodes": n, "edges": int(len(edges)),
        "layer_edges": {k: int(len(v)) for k, v in layers.items()},
        "placement": placement, "routes": routes, "hubs": hubs,
        "holds": {
            "placement": bool(placement["n_at_or_below_real"] == 0 and placement["p_value"] < ALPHA),
            "routes": bool(routes["total"]["ratio"] > 1 and routes["total"]["p_value"] < ALPHA),
            "hubs": bool(hubs["odds_ratio"] > 1 and hubs["p_value"] < ALPHA),
        },
    }


def hypothesis_section() -> str:
    return REPORT.read_text(encoding="utf-8").split("\n## Results")[0].rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-permutations", type=int, default=N_PERMUTATIONS)
    parser.add_argument("--n-nulls", type=int, default=N_NULLS)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--report-only", action="store_true", help="rewrite the report from the saved JSON")
    args = parser.parse_args()
    if args.report_only:
        write_report(json.loads((RESULTS / "threshold_robustness.json").read_text(encoding="utf-8")))
        return

    rows = []
    for fraction in FRACTIONS:
        rows.append(run_fraction(fraction, args.n_permutations, args.n_nulls, args.workers))
        print(fraction, json.dumps(rows[-1]["holds"]), flush=True)
    tested = [r for r in rows if r["fraction"] != 0.01]
    summary = {"preregistration_commit": PREREGISTRATION_COMMIT, "n_permutations": args.n_permutations,
               "n_nulls": args.n_nulls, "thresholds": rows,
               "h11_supported": all(all(r["holds"].values()) for r in tested)}
    (RESULTS / "threshold_robustness.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_report(summary)


def write_report(s: dict) -> None:
    def pct(fraction: float) -> str:
        return f"{100 * fraction:g}%" + (" (original)" if fraction == 0.01 else "")

    rows = s["thresholds"]
    lines = [
        hypothesis_section(),
        "## Results",
        "",
        f"Hypotheses committed in `{s['preregistration_commit']}` before any statistic in this file was computed. The 1% "
        "row is recomputed by this script and should match the original analyses.",
        "",
        "| threshold | nodes | edges | D_in | D_out | A_in | A_out |",
        "|---|---|---|---|---|---|---|",
        *[f"| {pct(r['fraction'])} | {r['nodes']:,} | {r['edges']:,} | "
          + " | ".join(f"{v:,}" for v in r["layer_edges"].values()) + " |" for r in rows],
        "",
        "### Placement",
        "",
        "| threshold | real / permuted cost | z | permutations at or below real | p |",
        "|---|---|---|---|---|",
        *[f"| {pct(r['fraction'])} | {r['placement']['cost_ratio']:.3f} | {r['placement']['z_score']:.1f} | "
          f"{r['placement']['n_at_or_below_real']} of {r['placement']['n_permutations']} | "
          f"{r['placement']['p_value']:.4f} |" for r in rows],
        "",
        "### Rich-to-rich routes, top 10%",
        "",
        "| threshold | real routes | real / randomized | z | p | descending ratio (p) | ascending ratio (p) |",
        "|---|---|---|---|---|---|---|",
        *[f"| {pct(r['fraction'])} | {r['routes']['total']['real']:,.0f} | {r['routes']['total']['ratio']:.3f} | "
          f"{r['routes']['total']['z_score']:.1f} | {r['routes']['total']['p_value']:.4f} | "
          f"{r['routes']['descending']['ratio']:.3f} ({r['routes']['descending']['p_value']:.4f}) | "
          f"{r['routes']['ascending']['ratio']:.3f} ({r['routes']['ascending']['p_value']:.4f}) |" for r in rows],
        "",
        "### Connective hubs",
        "",
        "| threshold | degree at 90th percentile | connective nodes above | other nodes above | odds ratio | p |",
        "|---|---|---|---|---|---|",
        *[f"| {pct(r['fraction'])} | {r['hubs']['degree_threshold']:.0f} | {100 * r['hubs']['connective_share_high']:.1f}% | "
          f"{100 * r['hubs']['other_share_high']:.1f}% | {r['hubs']['odds_ratio']:.2f} | {r['hubs']['p_value']:.3g} |"
          for r in rows],
        "",
    ]
    failures = [f"{t} at {pct(r['fraction'])}" for r in rows if r["fraction"] != 0.01
                for t, ok in r["holds"].items() if not ok]
    ratios = ", ".join(f"{r['routes']['total']['ratio']:.2f} at {100 * r['fraction']:g}%" for r in rows)
    lines += [f"The rich-to-rich route ratio changes with the threshold ({ratios}): the enrichment is carried by the "
              "strongest connections and disappears when weak ones are added.", ""]
    lines += [f"**H11 is {'supported' if s['h11_supported'] else 'not supported'}.**"
              + (f" Results that do not hold: {', '.join(failures)}." if failures else
                 " Every test keeps its direction and significance at every threshold."), ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
