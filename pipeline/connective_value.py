"""Compare the sensory-to-motor value of the neck connective with non-connective wiring of equal cost."""

import argparse
import json
from multiprocessing import Pool

import igraph as ig
import numpy as np
import pandas as pd

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, SEED
from pipeline.connective_richclub import compare, node_sets
from pipeline.connectivity_metrics import flow_capacity, reachable_pairs
from pipeline.figures import CONNECTIVE, MUTED, NULL, apply_style, plt
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

SENSORY_SUPERCLASSES = ("cb_sensory", "ol_sensory", "vnc_sensory", "sensory_ascending", "sensory_descending")
MOTOR_SUPERCLASSES = ("cb_motor", "vnc_motor")
N_NULLS = 1000
ALPHA = 0.05
NULL_SEED_OFFSET = 500_000
PREREGISTRATION_COMMIT = "e62c6df"
REPORT = RESULTS / "connective_value.md"
FAMILIES = {
    "crossing_cost": "neck-crossing edges vs random non-connective edges of equal cost (primary)",
    "incident_cost": "all connective-incident edges vs random non-connective edges of equal cost",
    "crossing_count": "neck-crossing edges vs random non-connective edges of equal count",
}


def sensory_motor_sets(graph: ig.Graph) -> dict[str, list[str]]:
    """Sensory and motor node names, whole-CNS and split by compartment."""
    names = np.asarray(graph.vs["name"])
    superclass = np.asarray(graph.vs["superclass"])
    compartment = np.asarray(graph.vs["compartment"], dtype=object)
    sensory, motor = np.isin(superclass, SENSORY_SUPERCLASSES), np.isin(superclass, MOTOR_SUPERCLASSES)
    return {
        "sensory": names[sensory].tolist(), "motor": names[motor].tolist(),
        "sensory_brain": names[sensory & (compartment == "brain")].tolist(),
        "sensory_vnc": names[sensory & (compartment == "vnc")].tolist(),
        "motor_brain": names[motor & (compartment == "brain")].tolist(),
        "motor_vnc": names[motor & (compartment == "vnc")].tolist(),
    }


def neck_crossing_mask(edges: np.ndarray, sets: dict[str, np.ndarray]) -> np.ndarray:
    """Edges joining a connective node to a partner on the far side of the neck: DN-V, V-DN, AN-B, B-AN."""
    s, t = edges[:, 0], edges[:, 1]
    dn, an, brain, vnc = sets["descending"], sets["ascending"], sets["brain"], sets["vnc"]
    return (dn[s] & vnc[t]) | (vnc[s] & dn[t]) | (an[s] & brain[t]) | (brain[s] & an[t])


def incident_mask(edges: np.ndarray, connective: np.ndarray) -> np.ndarray:
    """Edges with at least one connective endpoint."""
    return connective[edges[:, 0]] | connective[edges[:, 1]]


def take_until_cost(order: np.ndarray, lengths: np.ndarray, target: float) -> np.ndarray:
    """Leading edges of ``order`` whose summed length is closest to ``target`` without skipping any edge.

    Edges are added while the running total stays at or below the target; the next edge is also added if that
    brings the total closer to the target.
    """
    cumulative = np.cumsum(lengths[order])
    k = int(np.searchsorted(cumulative, target, side="right"))
    if k < len(order):
        below = cumulative[k - 1] if k > 0 else 0.0
        if abs(cumulative[k] - target) < abs(target - below):
            k += 1
    return order[:k]


def cost_matched_sample(candidates: np.ndarray, lengths: np.ndarray, target: float, rng: np.random.Generator) -> np.ndarray:
    """Random subset of candidate edge indices with total length matched to ``target``."""
    return take_until_cost(rng.permutation(candidates), lengths, target)


def count_matched_sample(candidates: np.ndarray, count: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform random subset of ``count`` candidate edge indices."""
    return rng.choice(candidates, size=count, replace=False)


def longest_matched(candidates: np.ndarray, lengths: np.ndarray, target: float) -> np.ndarray:
    """The longest candidate edges, in decreasing length, with total length matched to ``target``."""
    order = candidates[np.argsort(-lengths[candidates], kind="stable")]
    return take_until_cost(order, lengths, target)


def graph_without(edges: np.ndarray, names: list[str], removed: np.ndarray) -> ig.Graph:
    """Directed graph on the same named vertices with the edges at ``removed`` indices deleted."""
    keep = np.ones(len(edges), dtype=bool)
    keep[removed] = False
    graph = ig.Graph(n=len(names), edges=edges[keep].tolist(), directed=True)
    graph.vs["name"] = names
    return graph


def values(graph: ig.Graph, sm: dict[str, list[str]], with_pairs: bool = True) -> dict[str, int]:
    """Sensory-to-motor flow capacity (whole CNS and across the neck) and reachable pairs."""
    out = {
        "flow": flow_capacity(graph, sm["sensory"], sm["motor"]),
        "flow_brain_to_vnc": flow_capacity(graph, sm["sensory_brain"], sm["motor_vnc"]),
        "flow_vnc_to_brain": flow_capacity(graph, sm["sensory_vnc"], sm["motor_brain"]),
    }
    if with_pairs:
        out["pairs"] = reachable_pairs(graph, sm["sensory"], sm["motor"])
    return out


_WORKER: dict = {}


def _init_worker(edges, names, sm, candidates, lengths, targets, counts) -> None:
    _WORKER.update(edges=edges, names=names, sm=sm, candidates=candidates, lengths=lengths, targets=targets,
                   counts=counts)


def _null_job(job: tuple[str, int]) -> dict:
    family, index = job
    rng = np.random.default_rng(SEED + NULL_SEED_OFFSET + 1_000_000 * list(FAMILIES).index(family) + index)
    w = _WORKER
    if family == "crossing_count":
        removed = count_matched_sample(w["candidates"], w["counts"]["crossing"], rng)
    else:
        removed = cost_matched_sample(w["candidates"], w["lengths"], w["targets"][family.split("_")[0]], rng)
    result = values(graph_without(w["edges"], w["names"], removed), w["sm"])
    result.update(family=family, index=index, edges_removed=int(len(removed)),
                  cost_removed=float(w["lengths"][removed].sum()))
    return result


def plot(summary: dict, nulls: pd.DataFrame) -> None:
    apply_style()
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.4), dpi=200)
    titles = {"crossing_cost": "Neck-crossing edges, equal cost", "incident_cost": "All connective edges, equal cost",
              "crossing_count": "Neck-crossing edges, equal count"}
    metrics = {"flow": "sensory-to-motor flow capacity lost", "flow_brain_to_vnc": "brain sensory to nerve-cord motor flow lost"}
    for row, (metric, label) in enumerate(metrics.items()):
        for ax, family in zip(axes[row], FAMILIES):
            loss = summary["intact"][metric] - nulls.loc[nulls["family"] == family, metric]
            real = summary["families"][family][metric]
            ax.hist(loss, bins=40, color=NULL, alpha=0.6, edgecolor="none", label="random non-connective sets")
            ax.axvline(real["real"], color=CONNECTIVE, linewidth=2.2, label="connective")
            stats_line = f"ratio {real['ratio']:.2f}, z = {real['z_score']:.1f}, p = {real['p_value']:.4f}"
            ax.set_title(f"{titles[family]}\n{stats_line}", loc="left", fontsize=10)
            ax.set_xlabel(label)
            ax.set_ylabel("random sets" if family == "crossing_cost" else "")
            ax.grid(axis="x", visible=False)
    axes[0, 0].legend(loc="upper center", fontsize=7.5)
    fig.text(0.01, 0.01, f"Intact flow capacity {summary['intact']['flow']:,} (all sensory to all motor) and "
             f"{summary['intact']['flow_brain_to_vnc']:,} (brain sensory to nerve-cord motor). p is one-sided for a "
             "larger loss than random.", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(RESULTS / "connective_value.png")
    plt.close(fig)


def hypothesis_section() -> str:
    return REPORT.read_text(encoding="utf-8").split("\n## Procedure")[0].rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-nulls", type=int, default=N_NULLS)
    parser.add_argument("--workers", type=int, default=15)
    parser.add_argument("--report-only", action="store_true", help="redraw figure and report from saved results")
    args = parser.parse_args()
    if args.report_only:
        summary = json.loads((RESULTS / "connective_value.json").read_text(encoding="utf-8"))
        plot(summary, pd.read_csv(RESULTS / "connective_value_nulls.csv"))
        write_report(summary)
        return

    graph = load_spatial_graph()
    names = graph.vs["name"]
    edges = edge_array(graph)
    lengths = edge_costs(edges, positions_array(graph))
    sets = node_sets(graph)
    sm = sensory_motor_sets(graph)
    crossing = np.flatnonzero(neck_crossing_mask(edges, sets))
    incident = np.flatnonzero(incident_mask(edges, sets["connective"]))
    candidates = np.flatnonzero(~incident_mask(edges, sets["connective"]))
    targets = {"crossing": float(lengths[crossing].sum()), "incident": float(lengths[incident].sum())}
    counts = {"crossing": int(len(crossing)), "incident": int(len(incident))}
    longest = longest_matched(candidates, lengths, targets["crossing"])

    intact = values(graph_without(edges, names, np.array([], dtype=int)), sm)
    real = {
        "crossing": values(graph_without(edges, names, crossing), sm),
        "incident": values(graph_without(edges, names, incident), sm),
        "longest": values(graph_without(edges, names, longest), sm),
    }
    print("intact", intact, "real", real, flush=True)

    jobs = [(family, i) for family in FAMILIES for i in range(args.n_nulls)]
    with Pool(args.workers, initializer=_init_worker,
              initargs=(edges, names, sm, candidates, lengths, targets, counts)) as pool:
        rows = []
        for done, row in enumerate(pool.imap_unordered(_null_job, jobs, chunksize=4), start=1):
            rows.append(row)
            if done % 200 == 0:
                print(f"null sets: {done}/{len(jobs)}", flush=True)
    nulls = pd.DataFrame(rows).sort_values(["family", "index"]).reset_index(drop=True)
    nulls.to_csv(RESULTS / "connective_value_nulls.csv", index=False)

    metrics = ("flow", "pairs", "flow_brain_to_vnc", "flow_vnc_to_brain")
    families = {}
    for family in FAMILIES:
        removal = "incident" if family.startswith("incident") else "crossing"
        subset = nulls[nulls["family"] == family]
        families[family] = {
            metric: compare(intact[metric] - real[removal][metric], (intact[metric] - subset[metric]).to_numpy())
            for metric in metrics
        }
        families[family]["random_edges_removed"] = {"mean": float(subset["edges_removed"].mean()),
                                                     "min": int(subset["edges_removed"].min()),
                                                     "max": int(subset["edges_removed"].max())}
        families[family]["random_cost_ratio"] = {
            "min": float(subset["cost_removed"].min() / targets[removal]),
            "max": float(subset["cost_removed"].max() / targets[removal]),
        }
    summary = {
        "preregistration_commit": PREREGISTRATION_COMMIT, "n_nulls": args.n_nulls,
        "sets": {k: len(v) for k, v in sm.items()},
        "removal_sets": {
            "crossing": {"edges": counts["crossing"], "cost_um": targets["crossing"],
                         "mean_length_um": targets["crossing"] / counts["crossing"]},
            "incident": {"edges": counts["incident"], "cost_um": targets["incident"],
                         "mean_length_um": targets["incident"] / counts["incident"]},
            "longest_non_connective": {"edges": int(len(longest)), "cost_um": float(lengths[longest].sum()),
                                       "min_length_um": float(lengths[longest].min())},
            "non_connective_candidates": {"edges": int(len(candidates)),
                                          "mean_length_um": float(lengths[candidates].mean())},
        },
        "intact": intact, "real": real, "families": families,
    }
    (RESULTS / "connective_value.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    plot(summary, nulls)
    write_report(summary)
    print(json.dumps(families["crossing_cost"]["flow"], indent=1))


def write_report(s: dict) -> None:
    rs, intact = s["removal_sets"], s["intact"]
    primary = s["families"]["crossing_cost"]["flow"]
    primary_pairs = s["families"]["crossing_cost"]["pairs"]
    cross_bv = s["families"]["crossing_cost"]["flow_brain_to_vnc"]
    cross_vb = s["families"]["crossing_cost"]["flow_vnc_to_brain"]
    labels = {"flow": "flow capacity", "pairs": "reachable pairs",
              "flow_brain_to_vnc": "flow, brain sensory to nerve-cord motor",
              "flow_vnc_to_brain": "flow, nerve-cord sensory to brain motor"}

    def row(family: str, metric: str) -> str:
        c = s["families"][family][metric]
        return (f"| {labels[metric]} | {intact[metric]:,} | {c['real']:,.0f} | {c['null_mean']:,.1f} ± {c['null_sd']:,.1f} | "
                f"{c['n_at_or_above_real']} / {s['n_nulls']} | {c['ratio']:.2f} | {c['z_score']:.1f} | {c['p_value']:.4f} |")

    header = ["| value | intact | lost, connective | lost, random mean ± sd | random ≥ connective | ratio | z | p |",
              "|---|---|---|---|---|---|---|---|"]
    longest_loss = {m: intact[m] - s["real"]["longest"][m] for m in labels}
    lines = [
        hypothesis_section(),
        "## Procedure",
        "",
        f"Hypotheses committed in `{PREREGISTRATION_COMMIT}` before any statistic in this file was computed.",
        "",
        f"- Sensory nodes: {s['sets']['sensory']:,} ({s['sets']['sensory_brain']:,} brain, {s['sets']['sensory_vnc']:,} "
        f"nerve cord). Motor nodes: {s['sets']['motor']:,} ({s['sets']['motor_brain']:,} brain, "
        f"{s['sets']['motor_vnc']:,} nerve cord).",
        f"- Neck-crossing edges: {rs['crossing']['edges']:,}, total length {rs['crossing']['cost_um'] / 1e6:.2f} m, mean "
        f"{rs['crossing']['mean_length_um']:.0f} µm.",
        f"- All connective-incident edges: {rs['incident']['edges']:,}, total length {rs['incident']['cost_um'] / 1e6:.2f} m, "
        f"mean {rs['incident']['mean_length_um']:.0f} µm.",
        f"- Non-connective edges available for the null sets: {rs['non_connective_candidates']['edges']:,}, mean length "
        f"{rs['non_connective_candidates']['mean_length_um']:.0f} µm.",
    ]
    for family, label in FAMILIES.items():
        f = s["families"][family]
        lines.append(
            f"- {s['n_nulls']} random sets, {label}: {f['random_edges_removed']['mean']:,.0f} edges on average "
            f"({f['random_edges_removed']['min']:,}–{f['random_edges_removed']['max']:,}); achieved cost "
            f"{f['random_cost_ratio']['min']:.4f}–{f['random_cost_ratio']['max']:.4f} of the connective set's cost."
        )
    lines += [
        "",
        "## Result: neck-crossing edges against equal wiring cost (H4)",
        "",
        *header,
        *[row("crossing_cost", m) for m in labels],
        "",
        f"**H4 is {'supported' if primary['significant'] else 'not supported'}.** Cutting the {rs['crossing']['edges']:,} "
        f"neck-crossing edges removes {primary['real']:,.0f} units of sensory-to-motor flow capacity; random non-connective "
        f"wiring of the same total length removes {primary['null_mean']:,.1f} on average (ratio {primary['ratio']:.2f}, "
        f"z = {primary['z_score']:.1f}, p = {primary['p_value']:.4f}).",
        "",
        f"The loss is concentrated in one direction. Of the {intact['flow_brain_to_vnc']:,} units of flow from brain "
        f"sensory to nerve-cord motor nodes, the cut removes {cross_bv['real']:,.0f}, {cross_bv['ratio']:.2f} times the "
        f"random loss (p = {cross_bv['p_value']:.4f}); of the {intact['flow_vnc_to_brain']:,} units in the other "
        f"direction it removes {cross_vb['real']:,.0f}, {cross_vb['ratio']:.2f} times the random loss. Reachable "
        f"sensory-motor pairs are unchanged by the cut ({primary_pairs['real']:,.0f} lost), so every pair it touches "
        "stays joined by a path that avoids the neck-crossing edges.",
        "",
        "## Secondary: silencing every connective edge, equal cost",
        "",
        *header,
        *[row("incident_cost", m) for m in labels],
        "",
        "## Secondary: neck-crossing edges against equal edge count",
        "",
        *header,
        *[row("crossing_count", m) for m in labels],
        "",
        "## Secondary: the longest non-connective edges",
        "",
        f"The {rs['longest_non_connective']['edges']:,} longest non-connective edges (all at least "
        f"{rs['longest_non_connective']['min_length_um']:.0f} µm) match the neck-crossing edges in total length. Removing "
        "them loses: " + "; ".join(f"{labels[m]} {longest_loss[m]:,}" for m in labels) + ".",
        "",
        "![Connective value](connective_value.png)",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
