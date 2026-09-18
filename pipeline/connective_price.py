"""Price (wire length) and value (flow lost on removal) of each descending and ascending cell type's neck-crossing edges."""

import argparse
import json
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy import stats

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, markdown_table
from pipeline.connective_richclub import node_sets
from pipeline.connective_value import graph_without, neck_crossing_mask, sensory_motor_sets, values
from pipeline.figures import CONNECTIVE, NULL, apply_style, plt
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

ALPHA = 0.05
N_WORKERS = 12
N_LISTED = 15
PREREGISTRATION_COMMIT = "73fba33"
REPORT = RESULTS / "connective_price.md"
DIRECTION = {"descending": "flow_brain_to_vnc", "ascending": "flow_vnc_to_brain"}

_WORKER: dict = {}


def crossing_edges_by_node(edges: np.ndarray, crossing: np.ndarray, connective: np.ndarray) -> dict[int, np.ndarray]:
    """Indices of neck-crossing edges grouped by their connective endpoint.

    Args:
        edges: (m, 2) edge array.
        crossing: length-m boolean mask of neck-crossing edges.
        connective: length-n boolean mask of connective nodes.

    Returns:
        Mapping from connective node index to the indices of its neck-crossing edges, for nodes that have any.
    """
    index = np.flatnonzero(crossing)
    s, t = edges[index, 0], edges[index, 1]
    if (connective[s] & connective[t]).any():
        raise ValueError("a neck-crossing edge joins two connective nodes")
    node = np.where(connective[s], s, t)
    order = np.argsort(node, kind="stable")
    nodes, starts = np.unique(node[order], return_index=True)
    return {int(v): index[order][a:b] for v, a, b in zip(nodes, starts, np.r_[starts[1:], len(order)])}


def partial_spearman(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple[float, float]:
    """Partial rank correlation of x and y given z, with its one-sided (positive) p-value.

    Each of rank(x) and rank(y) is regressed linearly on rank(z); the Pearson correlation of the residuals is returned.
    """
    rz = stats.rankdata(z)
    residuals = []
    for v in (x, y):
        rv = stats.rankdata(v)
        slope, intercept = np.polyfit(rz, rv, 1)
        residuals.append(rv - (slope * rz + intercept))
    result = stats.pearsonr(*residuals, alternative="greater")
    return float(result.statistic), float(result.pvalue)


def _init_worker(edges, names, sm) -> None:
    _WORKER.update(edges=edges, names=names, sm=sm)


def _removal_job(job: tuple[int, np.ndarray]) -> dict:
    node, removed = job
    result = values(graph_without(_WORKER["edges"], _WORKER["names"], removed), _WORKER["sm"], with_pairs=False)
    return {"index": node, **result}


def plot(frame: pd.DataFrame, tests: dict) -> None:
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), dpi=200)
    for ax, (group, color) in zip(axes, (("descending", CONNECTIVE), ("ascending", NULL))):
        part = frame[frame["direction"] == group]
        ax.scatter(part["price_um"] / 1000, part["value"], s=10, color=color, alpha=0.6, linewidths=0)
        ax.set_xscale("log")
        ax.set_yscale("symlog", linthresh=1)
        t = tests[group]
        ax.set_title(f"{group.capitalize()} cell types (n = {t['n']})\nSpearman ρ = {t['spearman_rho']:.2f}, "
                     f"partial ρ given edge count = {t['partial_rho']:.2f}", loc="left", fontsize=10)
        ax.set_xlabel("price: neck-crossing wire (mm)")
        ax.set_ylabel("value: " + ("brain-to-nerve-cord" if group == "descending" else "nerve-cord-to-brain")
                      + " flow lost")
    fig.tight_layout()
    fig.savefig(RESULTS / "connective_price.png")
    plt.close(fig)


def hypothesis_section() -> str:
    return REPORT.read_text(encoding="utf-8").split("\n## Results")[0].rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=N_WORKERS)
    parser.add_argument("--report-only", action="store_true", help="redraw figure and report from saved results")
    args = parser.parse_args()
    if args.report_only:
        summary = json.loads((RESULTS / "connective_price.json").read_text(encoding="utf-8"))
        frame = pd.read_csv(RESULTS / "connective_price.csv")
        plot(frame, summary["tests"])
        write_report(summary, frame)
        return

    graph = load_spatial_graph()
    names = graph.vs["name"]
    edges = edge_array(graph)
    lengths = edge_costs(edges, positions_array(graph))
    sets = node_sets(graph)
    sm = sensory_motor_sets(graph)
    by_node = crossing_edges_by_node(edges, neck_crossing_mask(edges, sets), sets["connective"])
    intact = values(graph_without(edges, names, np.array([], dtype=int)), sm, with_pairs=False)

    with Pool(args.workers, initializer=_init_worker, initargs=(edges, names, sm)) as pool:
        rows = []
        for done, row in enumerate(pool.imap_unordered(_removal_job, by_node.items(), chunksize=4), start=1):
            rows.append(row)
            if done % 200 == 0:
                print(f"removals: {done}/{len(by_node)}", flush=True)

    removal = pd.DataFrame(rows).set_index("index").sort_index()
    frame = pd.DataFrame({
        "node": [names[i] for i in removal.index],
        "cell_type": [graph.vs[i]["cell_type"] for i in removal.index],
        "side": [graph.vs[i]["side"] for i in removal.index],
        "direction": ["descending" if sets["descending"][i] else "ascending" for i in removal.index],
        "edges": [len(by_node[i]) for i in removal.index],
        "price_um": [float(lengths[by_node[i]].sum()) for i in removal.index],
    })
    for metric in ("flow", "flow_brain_to_vnc", "flow_vnc_to_brain"):
        frame[f"lost_{metric}"] = intact[metric] - removal[metric].to_numpy()
    frame["value"] = np.where(frame["direction"] == "descending", frame["lost_flow_brain_to_vnc"],
                              frame["lost_flow_vnc_to_brain"])
    frame["value_per_mm"] = frame["value"] / (frame["price_um"] / 1000)
    if (frame[[c for c in frame if c.startswith("lost_")]] < 0).any().any():
        raise RuntimeError("removing edges increased a flow capacity")

    tests = {}
    for group in DIRECTION:
        part = frame[frame["direction"] == group]
        rho = stats.spearmanr(part["price_um"], part["value"], alternative="greater")
        partial_rho, partial_p = partial_spearman(part["price_um"].to_numpy(), part["value"].to_numpy(),
                                                  part["edges"].to_numpy())
        rho_count = stats.spearmanr(part["edges"], part["value"])
        tests[group] = {
            "n": len(part), "zero_value": int((part["value"] == 0).sum()),
            "spearman_rho": float(rho.statistic), "p_value": float(rho.pvalue),
            "partial_rho": partial_rho, "partial_p_value": partial_p,
            "edge_count_value_rho": float(rho_count.statistic),
            "total_price_um": float(part["price_um"].sum()), "total_value": int(part["value"].sum()),
        }
    summary = {
        "preregistration_commit": PREREGISTRATION_COMMIT, "intact": intact, "tests": tests,
        "h10_supported": all(t["p_value"] < ALPHA for t in tests.values()),
        "h10b_supported": all(t["partial_p_value"] < ALPHA for t in tests.values()),
    }
    frame.sort_values("value", ascending=False).to_csv(RESULTS / "connective_price.csv", index=False, float_format="%.2f")
    (RESULTS / "connective_price.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    plot(frame, tests)
    write_report(summary, frame)


def write_report(s: dict, frame: pd.DataFrame) -> None:
    def verdict(flag: bool) -> str:
        return "supported" if flag else "not supported"

    def listing(part: pd.DataFrame, column: str) -> str:
        table = part.nlargest(N_LISTED, column)[["node", "edges", "price_um", "value", "value_per_mm"]].copy()
        table["price_um"] = (table["price_um"] / 1000).map("{:.1f} mm".format)
        table["value_per_mm"] = table["value_per_mm"].map("{:.2f}".format)
        renamed = table.rename(columns={"price_um": "price", "value_per_mm": "value per mm"})
        return "\n".join(markdown_table(renamed))

    lines = [
        hypothesis_section(),
        "## Results",
        "",
        f"Hypotheses committed in `{s['preregistration_commit']}` before any statistic in this file was computed. "
        f"Intact flow capacity: {s['intact']['flow_brain_to_vnc']:,} brain sensory to nerve-cord motor, "
        f"{s['intact']['flow_vnc_to_brain']:,} nerve-cord sensory to brain motor.",
        "",
        "| nodes | n | no flow lost | Spearman ρ (price, value) | p | partial ρ given edge count | p | ρ (edge count, value) |",
        "|---|---|---|---|---|---|---|---|",
        *[
            f"| {g} | {t['n']:,} | {t['zero_value']:,} | {t['spearman_rho']:.3f} | {t['p_value']:.3g} | "
            f"{t['partial_rho']:.3f} | {t['partial_p_value']:.3g} | {t['edge_count_value_rho']:.3f} |"
            for g, t in s["tests"].items()
        ],
        "",
        f"**H10 is {verdict(s['h10_supported'])}. H10b is {verdict(s['h10b_supported'])}.**",
        "",
        f"Removing the neck-crossing edges of a single cell type usually costs no flow at all "
        f"({s['tests']['descending']['zero_value']:,} of {s['tests']['descending']['n']:,} descending and "
        f"{s['tests']['ascending']['zero_value']:,} of {s['tests']['ascending']['n']:,} ascending nodes): the "
        "remaining wiring supports the same maximum flow. Among descending nodes, price and value rise together only because "
        f"both rise with the number of connections (ρ between edge count and value "
        f"{s['tests']['descending']['edge_count_value_rho']:.2f}); at a fixed number of connections, longer wiring "
        "buys no more flow. Among ascending nodes price and value are unrelated, and the most expensive ascending "
        "types carry no nerve-cord-to-brain sensory-to-motor flow of their own.",
        "",
    ]
    for group in DIRECTION:
        part = frame[frame["direction"] == group]
        lines += [
            f"### {group.capitalize()} cell types with the largest value",
            "",
            listing(part, "value"),
            "",
            f"### {group.capitalize()} cell types with the largest price",
            "",
            listing(part, "price_um"),
            "",
        ]
    lines += ["Values are units of flow capacity lost; every node's figures are in `connective_price.csv`.", "",
              "![Connective price and value](connective_price.png)", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
