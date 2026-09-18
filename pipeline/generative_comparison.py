"""Sample synthetic graphs from the fitted generative models and compare their structure with the real graph."""

import argparse
import json
from multiprocessing import Pool

import igraph as ig
import numpy as np
import pandas as pd
from scipy import stats

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, SEED
from pipeline.connective_richclub import TOP_FRACTION, layer_edges, node_sets, partner_richness, rich_mask, route_counts
from pipeline.connective_value import neck_crossing_mask, sensory_motor_sets
from pipeline.connectivity_metrics import flow_capacity, reachable_pairs
from pipeline.figures import CONNECTIVE, MUTED, NULL, REAL, apply_style, plt
from pipeline.generative_model import MODEL_JSON, REPORT, logit_path
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

N_SYNTHETIC = 50
SYNTHETIC_SEED_OFFSET = 700_000
BLOCK = 512
MODELS = ("G", "G_deg")
PROPERTIES = {
    "in_degree_sd": "in-degree, standard deviation",
    "in_degree_max": "in-degree, maximum",
    "out_degree_sd": "out-degree, standard deviation",
    "out_degree_max": "out-degree, maximum",
    "total_cost_um": "total wiring cost (µm)",
    "median_length_um": "median edge length (µm)",
    "cross_compartment_fraction": "fraction of edges joining brain and nerve cord",
    "reciprocity": "reciprocity",
    "transitivity": "global transitivity (undirected)",
    "flow": "sensory-to-motor flow capacity",
    "pairs": "sensory-to-motor reachable pairs",
    "neck_crossing_edges": "neck-crossing edges",
    "rich_routes": "rich-to-rich routes through the connective (top 10%)",
}


def sample_graph(logits: np.ndarray, shift: float, rng: np.random.Generator) -> np.ndarray:
    """Edges of one synthetic graph: each ordered pair independently present with probability sigmoid(logit + shift)."""
    n = logits.shape[0]
    parts = []
    for start in range(0, n, BLOCK):
        block = np.asarray(logits[start:start + BLOCK], dtype=np.float32)
        with np.errstate(over="ignore"):
            p = 1.0 / (1.0 + np.exp(-(block + np.float32(shift))))
        rows, cols = np.nonzero(rng.random(block.shape, dtype=np.float32) < p)
        parts.append(np.column_stack([rows + start, cols]))
    return np.vstack(parts).astype(np.int64)


def graph_properties(edges: np.ndarray, context: dict) -> dict:
    """Every compared property of a graph given as an (m, 2) edge array over the real node set."""
    n, names = context["n"], context["names"]
    indeg, outdeg = np.bincount(edges[:, 1], minlength=n), np.bincount(edges[:, 0], minlength=n)
    lengths = edge_costs(edges, context["positions"])
    keys = edges[:, 0] * n + edges[:, 1]
    reverse = edges[:, 1] * n + edges[:, 0]
    graph = ig.Graph(n=n, edges=edges.tolist(), directed=True)
    graph.vs["name"] = names
    sets, sm = context["sets"], context["sm"]
    richness = partner_richness(edges, sets["connective"])
    rich_brain = rich_mask(richness, sets["brain"], TOP_FRACTION)
    rich_vnc = rich_mask(richness, sets["vnc"], TOP_FRACTION)
    compartment = context["compartment"]
    return {
        "edges": int(len(edges)),
        "in_degree_sd": float(indeg.std()), "in_degree_max": int(indeg.max()),
        "out_degree_sd": float(outdeg.std()), "out_degree_max": int(outdeg.max()),
        "total_cost_um": float(lengths.sum()), "median_length_um": float(np.median(lengths)),
        "cross_compartment_fraction": float(np.mean(compartment[edges[:, 0]] != compartment[edges[:, 1]])),
        "reciprocity": float(np.isin(reverse, keys).mean()),
        "transitivity": float(graph.transitivity_undirected()),
        "flow": flow_capacity(graph, sm["sensory"], sm["motor"]),
        "pairs": reachable_pairs(graph, sm["sensory"], sm["motor"]),
        "neck_crossing_edges": int(neck_crossing_mask(edges, sets).sum()),
        "rich_routes": route_counts(layer_edges(edges, sets), rich_brain, rich_vnc)["total"],
        "_in_degree": indeg, "_out_degree": outdeg,
    }


_WORKER: dict = {}


def _init_worker(context: dict, shifts: dict) -> None:
    _WORKER.update(context=context, shifts=shifts, logits={})


def _synthetic_job(job: tuple[str, int]) -> dict:
    model, index = job
    if model not in _WORKER["logits"]:
        _WORKER["logits"][model] = np.load(logit_path(model), mmap_mode="r")
    rng = np.random.default_rng(SEED + SYNTHETIC_SEED_OFFSET + 1000 * MODELS.index(model) + index)
    edges = sample_graph(_WORKER["logits"][model], _WORKER["shifts"][model], rng)
    props = graph_properties(edges, _WORKER["context"])
    props.update(model=model, index=index)
    return props


def plot(real: dict, table: pd.DataFrame, degrees: dict) -> None:
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.6), dpi=200, gridspec_kw={"width_ratios": [1.6, 1, 1]})
    ax = axes[0]
    labels = list(PROPERTIES)
    y = np.arange(len(labels))
    for offset, model, color in ((-0.15, "G", NULL), (0.15, "G_deg", CONNECTIVE)):
        rows = table[table["model"] == model]
        z = [(real[p] - rows[p].mean()) / rows[p].std(ddof=1) if rows[p].std(ddof=1) > 0 else np.nan for p in labels]
        ax.scatter(np.clip(z, -30, 30), y + offset, color=color, s=28, zorder=3,
                   label="distance + compartment + class" if model == "G" else "... + degree")
    ax.axvspan(-1.96, 1.96, color=MUTED, alpha=0.15, linewidth=0)
    ax.set_yticks(y, [PROPERTIES[p] for p in labels], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(-31, 31)
    ax.set_xlabel("real value, in standard deviations of 50 synthetic graphs (clipped at ±30)")
    ax.set_title("Real graph against model-generated graphs", loc="left")
    ax.legend(loc="lower right", fontsize=7.5)
    ax.grid(axis="y", visible=False)
    for ax, key, title in ((axes[1], "_in_degree", "In-degree"), (axes[2], "_out_degree", "Out-degree")):
        for label, values, color in (("real", degrees["real"][key], REAL), ("model G", degrees["G"][key], NULL),
                                     ("model G+deg", degrees["G_deg"][key], CONNECTIVE)):
            v = np.sort(values)
            ax.plot(v[::-1], np.arange(1, len(v) + 1) / len(v), color=color, linewidth=1.6, label=label)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"{title} distribution", loc="left")
        ax.set_xlabel("degree")
        ax.set_ylabel("fraction of nodes with at least this degree")
        ax.legend(loc="lower left", fontsize=7.5)
    fig.text(0.01, 0.01, "Grey band: within ±1.96 standard deviations. One synthetic graph per model shown in the degree "
             "panels.", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(RESULTS / "generative_comparison.png")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-synthetic", type=int, default=N_SYNTHETIC)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--report-only", action="store_true", help="rewrite the report from the saved JSON")
    args = parser.parse_args()
    if args.report_only:
        write_report(json.loads((RESULTS / "generative_comparison.json").read_text(encoding="utf-8")))
        return

    graph = load_spatial_graph()
    fit_summary = json.loads(MODEL_JSON.read_text(encoding="utf-8"))
    shifts = {m: fit_summary["models"][m]["shift_to_match_edges"] for m in MODELS}
    context = {
        "n": graph.vcount(), "names": graph.vs["name"], "positions": positions_array(graph),
        "compartment": np.asarray(graph.vs["compartment"], dtype=object), "sets": node_sets(graph),
        "sm": sensory_motor_sets(graph),
    }
    real = graph_properties(edge_array(graph), context)
    jobs = [(m, i) for m in MODELS for i in range(args.n_synthetic)]
    with Pool(args.workers, initializer=_init_worker, initargs=(context, shifts)) as pool:
        rows = []
        for done, row in enumerate(pool.imap_unordered(_synthetic_job, jobs), start=1):
            rows.append(row)
            if done % 10 == 0:
                print(f"synthetic graphs: {done}/{len(jobs)}", flush=True)
    rows.sort(key=lambda r: (MODELS.index(r["model"]), r["index"]))
    degrees = {"real": real}
    for m in MODELS:
        degrees[m] = next(r for r in rows if r["model"] == m)
    ks = {m: {key: [float(stats.ks_2samp(real[key], r[key]).statistic) for r in rows if r["model"] == m]
              for key in ("_in_degree", "_out_degree")} for m in MODELS}
    table = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])
    table.to_csv(RESULTS / "generative_comparison.csv", index=False, float_format="%.6g")

    comparison = {}
    for m in MODELS:
        subset = table[table["model"] == m]
        comparison[m] = {"edges": {"mean": float(subset["edges"].mean()), "min": int(subset["edges"].min()),
                                   "max": int(subset["edges"].max())}, "properties": {}}
        for p in PROPERTIES:
            lo, hi = np.percentile(subset[p], [2.5, 97.5])
            comparison[m]["properties"][p] = {
                "real": float(real[p]), "synthetic_mean": float(subset[p].mean()),
                "synthetic_sd": float(subset[p].std(ddof=1)), "interval_95": [float(lo), float(hi)],
                "reproduced": bool(lo <= real[p] <= hi),
            }
        props = comparison[m]["properties"]
        comparison[m]["fraction_reproduced"] = sum(v["reproduced"] for v in props.values()) / len(props)
        comparison[m]["ks_in_degree_mean"] = float(np.mean(ks[m]["_in_degree"]))
        comparison[m]["ks_out_degree_mean"] = float(np.mean(ks[m]["_out_degree"]))
    summary = {"n_synthetic": args.n_synthetic, "shifts": shifts, "real_edges": real["edges"], "models": comparison}
    (RESULTS / "generative_comparison.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    plot(real, table, degrees)
    write_report(summary)
    for m in MODELS:
        print(m, f"reproduced {comparison[m]['fraction_reproduced']:.2f}",
              [p for p, v in comparison[m]["properties"].items() if v["reproduced"]], flush=True)


def write_report(s: dict) -> None:
    text = REPORT.read_text(encoding="utf-8").split("\n## Synthetic graphs")[0].rstrip() + "\n"
    names = {"G": "model G", "G_deg": "model G+deg"}

    def fmt(value: float) -> str:
        return f"{value:,.0f}" if abs(value) >= 100 else f"{value:.4g}"

    lines = [text, "## Synthetic graphs", ""]
    for m in MODELS:
        c = s["models"][m]
        lines.append(f"- {names[m]}: {s['n_synthetic']} graphs, {c['edges']['mean']:,.0f} edges on average "
                     f"({c['edges']['min']:,}–{c['edges']['max']:,}; real {s['real_edges']:,}); mean Kolmogorov-Smirnov "
                     f"distance to the real degree distribution {c['ks_in_degree_mean']:.3f} (in) and "
                     f"{c['ks_out_degree_mean']:.3f} (out).")
    lines += [
        "",
        "| property | real | model G: synthetic mean [central 95%] | reproduced | model G+deg: synthetic mean [central 95%] | "
        "reproduced |",
        "|---|---|---|---|---|---|",
    ]
    for p, label in PROPERTIES.items():
        cells = []
        for m in MODELS:
            v = s["models"][m]["properties"][p]
            cells.append(f"{fmt(v['synthetic_mean'])} [{fmt(v['interval_95'][0])}–{fmt(v['interval_95'][1])}] | "
                         f"{'yes' if v['reproduced'] else 'no'}")
        lines.append(f"| {label} | {fmt(s['models']['G']['properties'][p]['real'])} | {cells[0]} | {cells[1]} |")
    for m in MODELS:
        props = s["models"][m]["properties"]
        yes = [PROPERTIES[p] for p, v in props.items() if v["reproduced"]]
        no = [PROPERTIES[p] for p, v in props.items() if not v["reproduced"]]
        lines += [
            "",
            f"**{names[m][0].upper() + names[m][1:]} reproduces {len(yes)} of {len(props)} properties "
            f"({100 * s['models'][m]['fraction_reproduced']:.0f}%).** Reproduced: {', '.join(yes) if yes else 'none'}. "
            f"Not reproduced: {', '.join(no) if no else 'none'}.",
        ]
    g, d = s["models"]["G"]["properties"], s["models"]["G_deg"]["properties"]

    def times(p: str, props: dict) -> float:
        return props[p]["real"] / props[p]["synthetic_mean"]

    lines += [
        "",
        f"Neither model produces the local structure of the real graph: it has {times('reciprocity', g):.0f} and "
        f"{times('reciprocity', d):.0f} times the reciprocity of model G and model G+deg graphs, and "
        f"{times('transitivity', g):.0f} and {times('transitivity', d):.0f} times their transitivity, which is expected "
        "of models that draw every ordered pair independently. Adding degree fixes the out-degree distribution "
        f"(Kolmogorov-Smirnov distance {s['models']['G_deg']['ks_out_degree_mean']:.3f} against "
        f"{s['models']['G']['ks_out_degree_mean']:.3f}) but makes rich-to-rich routing through the connective "
        f"{d['rich_routes']['synthetic_mean'] / d['rich_routes']['real']:.1f} times too frequent. Distance, compartment "
        "and cell class alone produce as many rich-to-rich routes as the real graph: the enrichment over "
        "degree-preserving rewiring reported in `connective_richclub.md` is matched by a model built from those three "
        "factors, without the real degree sequence.",
        "",
        "![Generative model comparison](generative_comparison.png)",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
