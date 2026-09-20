"""Ask what the wiring budget buys by removing connections from each end of the length distribution."""

import json

import igraph as ig
import numpy as np
import pandas as pd

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, SEED, markdown_table
from pipeline.figures import CONNECTIVE, INK_SECONDARY, MUTED, NULL, REAL, apply_style, plt
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

WIRE_FRACTIONS = (0.0, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20,
                  0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60)
N_SOURCES = 300
N_RANDOM = 5
REFERENCE_FRACTION = 0.25
HALF = 0.5
SOURCE_SEED_OFFSET = 700_000
RANDOM_SEED_OFFSET = 750_000
LONGEST, RANDOM, SHORTEST = "longest first", "random, matched count", "shortest first"
REPORT = RESULTS / "length_tradeoff.md"


def cut_counts(lengths: np.ndarray, order: np.ndarray, fractions) -> np.ndarray:
    """How many connections a removal schedule must take to have removed each share of the wire.

    Args:
        lengths: connection lengths in micrometers.
        order: the order connections are removed in, as indices into ``lengths``.
        fractions: shares of the total wire to reach.

    Returns:
        One count per fraction: the fewest leading connections of ``order`` whose lengths sum to at least
        that share of the total.
    """
    cumulative = np.cumsum(lengths[order])
    targets = np.asarray(fractions, dtype=float) * cumulative[-1]
    counts = np.searchsorted(cumulative, targets, side="left") + 1
    return np.where(np.asarray(fractions) <= 0, 0, np.minimum(counts, len(order)))


def largest_component(n_vertices: int, edges: np.ndarray) -> int:
    """Number of vertices in the largest weakly connected component of a directed edge set."""
    graph = ig.Graph(n=n_vertices, edges=edges.tolist(), directed=True)
    return int(max(graph.connected_components(mode="weak").sizes()))


def sampled_efficiency(n_vertices: int, edges: np.ndarray, sources: np.ndarray) -> float:
    """Mean reciprocal directed distance from each sampled source to every other vertex.

    Pairs with no directed path contribute zero, so the measure stays defined as removal disconnects the
    graph. It is the global efficiency of the graph estimated on the sampled rows of its distance matrix.
    """
    graph = ig.Graph(n=n_vertices, edges=edges.tolist(), directed=True)
    distances = np.asarray(graph.distances(source=sources.tolist(), mode="out"), dtype=float)
    with np.errstate(divide="ignore"):
        reciprocal = np.where(np.isfinite(distances) & (distances > 0), 1.0 / distances, 0.0)
    return float(reciprocal.sum() / (len(sources) * (n_vertices - 1)))


def removal_point(n_vertices: int, edges: np.ndarray, lengths: np.ndarray, order: np.ndarray, count: int,
                  sources: np.ndarray) -> dict:
    """The graph left after removing the first ``count`` connections of ``order``, measured two ways."""
    keep = np.ones(len(order), dtype=bool)
    keep[order[:count]] = False
    return {
        "edges_removed": int(count),
        "wire_removed_um": round(float(lengths[order[:count]].sum()), 1),
        "largest_component": largest_component(n_vertices, edges[keep]),
        "efficiency": round(sampled_efficiency(n_vertices, edges[keep], sources), 6),
    }


def removal_curve(n_vertices: int, edges: np.ndarray, lengths: np.ndarray, order: np.ndarray,
                  counts: np.ndarray, sources: np.ndarray) -> list[dict]:
    """One measured point per entry of ``counts``, with each quantity also given as a share of its whole."""
    baseline = None
    rows = []
    for count in counts:
        row = removal_point(n_vertices, edges, lengths, order, int(count), sources)
        baseline = baseline or row["efficiency"]
        rows.append(row | {
            "edges_removed_share": round(count / len(order), 5),
            "wire_removed_share": round(row["wire_removed_um"] / float(lengths.sum()), 5),
            "largest_component_share": round(row["largest_component"] / n_vertices, 5),
            "efficiency_share": round(row["efficiency"] / baseline, 5),
        })
    return rows


def pooled_curve(curves: list[list[dict]]) -> list[dict]:
    """Mean and spread over repeats of the same schedule, point by point."""
    rows = []
    for point in zip(*curves):
        row = {"edges_removed": point[0]["edges_removed"], "edges_removed_share": point[0]["edges_removed_share"]}
        for key in ("wire_removed_um", "wire_removed_share", "largest_component", "largest_component_share",
                    "efficiency", "efficiency_share"):
            values = np.array([p[key] for p in point], dtype=float)
            row[key] = round(float(values.mean()), 6 if "share" in key or key == "efficiency" else 1)
            row[f"{key}_sd"] = round(float(values.std(ddof=1)), 6 if "share" in key or key == "efficiency" else 1)
        rows.append(row)
    return rows


def wire_at_level(rows: list[dict], level: float) -> float | None:
    """The share of the wire removed when efficiency first falls to ``level`` of its starting value.

    Linear interpolation between the two bracketing sampled points; None when the curve never gets there.
    """
    for before, after in zip(rows, rows[1:]):
        if after["efficiency_share"] <= level <= before["efficiency_share"]:
            span = before["efficiency_share"] - after["efficiency_share"]
            if span == 0:
                return round(before["wire_removed_share"], 5)
            weight = (before["efficiency_share"] - level) / span
            return round(before["wire_removed_share"]
                         + weight * (after["wire_removed_share"] - before["wire_removed_share"]), 5)
    return None


def tradeoff(graph: ig.Graph) -> dict:
    """Three removal schedules over the same graph, and what each costs in connectivity per micrometre."""
    positions = positions_array(graph)
    edges = edge_array(graph)
    lengths = edge_costs(edges, positions)
    n = graph.vcount()
    sources = np.random.default_rng(SEED + SOURCE_SEED_OFFSET).choice(n, N_SOURCES, replace=False)
    sources.sort()

    longest = np.argsort(-lengths, kind="stable")
    shortest = longest[::-1].copy()
    long_counts = cut_counts(lengths, longest, WIRE_FRACTIONS)
    short_counts = cut_counts(lengths, shortest, WIRE_FRACTIONS)

    curves = {
        LONGEST: removal_curve(n, edges, lengths, longest, long_counts, sources),
        SHORTEST: removal_curve(n, edges, lengths, shortest, short_counts, sources),
    }
    # Matched on the number of connections the longest-first schedule removes, not on the wire.
    repeats = [removal_curve(n, edges, lengths,
                             np.random.default_rng(SEED + RANDOM_SEED_OFFSET + i).permutation(len(edges)),
                             long_counts, sources)
               for i in range(N_RANDOM)]
    curves[RANDOM] = pooled_curve(repeats)

    reference = WIRE_FRACTIONS.index(REFERENCE_FRACTION)
    at_reference = {name: rows[reference] for name, rows in curves.items()}
    half = {name: wire_at_level(rows, HALF) for name, rows in curves.items()}
    total_wire = float(lengths.sum())
    comparison = {
        "reference_wire_fraction": REFERENCE_FRACTION,
        "at_reference": at_reference,
        "wire_share_to_halve_efficiency": half,
        "efficiency_lost_per_metre": {
            name: round((1 - rows[reference]["efficiency_share"]) / (rows[reference]["wire_removed_um"] / 1e6), 6)
            for name, rows in curves.items()
        },
    }
    if half[LONGEST] and half[SHORTEST]:
        comparison["halving_wire_ratio"] = round(half[LONGEST] / half[SHORTEST], 3)

    return {
        "graph": {"nodes": n, "edges": len(edges), "total_wire_um": round(total_wire, 1),
                  "mean_length_um": round(float(lengths.mean()), 2),
                  "median_length_um": round(float(np.median(lengths)), 2)},
        "sampling": {"wire_fractions": list(WIRE_FRACTIONS), "points": len(WIRE_FRACTIONS),
                     "sources": N_SOURCES, "random_repeats": N_RANDOM,
                     "source_seed": SEED + SOURCE_SEED_OFFSET},
        "baseline": {"largest_component": curves[LONGEST][0]["largest_component"],
                     "largest_component_share": curves[LONGEST][0]["largest_component_share"],
                     "efficiency": curves[LONGEST][0]["efficiency"]},
        "curves": curves,
        "comparison": comparison,
    }


def figure(result: dict, path) -> None:
    """Connectivity against the wire removed, against the connections removed, and the component it leaves."""
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(15.6, 4.8))
    colors = {LONGEST: REAL, RANDOM: NULL, SHORTEST: CONNECTIVE}
    curves = result["curves"]

    for name, rows in curves.items():
        x = np.array([r["wire_removed_share"] for r in rows]) * 100
        y = np.array([r["efficiency_share"] for r in rows]) * 100
        axes[0].plot(x, y, color=colors[name], marker="o", markersize=3.5, linewidth=1.8, label=name)
        if "efficiency_share_sd" in rows[0]:
            sd = np.array([r["efficiency_share_sd"] for r in rows]) * 100
            axes[0].fill_between(x, y - sd, y + sd, color=colors[name], alpha=0.2, linewidth=0)
    axes[0].axhline(50, color=MUTED, linestyle="--", linewidth=1)
    axes[0].set_xlabel("wire removed (%)")
    axes[0].set_ylabel("efficiency, share of the whole graph's (%)")
    axes[0].set_title("What a micrometre of wire buys", loc="left", fontsize=10.5)
    axes[0].legend(loc="upper right", fontsize=8.5)
    half = result["comparison"]["wire_share_to_halve_efficiency"]
    for name in (LONGEST, SHORTEST):
        if half[name]:
            axes[0].plot([half[name] * 100], [50], "o", color=colors[name], markersize=6)
            axes[0].annotate(f"{half[name] * 100:.0f}%", (half[name] * 100, 50), textcoords="offset points",
                             xytext=(4, 8), fontsize=8.5, color=INK_SECONDARY)

    for name, rows in curves.items():
        axes[1].plot(np.array([r["edges_removed_share"] for r in rows]) * 100,
                     np.array([r["efficiency_share"] for r in rows]) * 100,
                     color=colors[name], marker="o", markersize=3.5, linewidth=1.8, label=name)
    axes[1].set_xlabel("connections removed (%)")
    axes[1].set_ylabel("efficiency, share of the whole graph's (%)")
    axes[1].set_title("What a connection buys", loc="left", fontsize=10.5)
    axes[1].legend(loc="upper right", fontsize=8.5)

    for name, rows in curves.items():
        axes[2].plot(np.array([r["wire_removed_share"] for r in rows]) * 100,
                     np.array([r["largest_component_share"] for r in rows]) * 100,
                     color=colors[name], marker="o", markersize=3.5, linewidth=1.8, label=name)
    axes[2].set_xlabel("wire removed (%)")
    axes[2].set_ylabel("largest component, share of all nodes (%)")
    axes[2].set_ylim(0, 105)
    axes[2].set_title("The graph barely fragments", loc="left", fontsize=10.5)
    axes[2].legend(loc="lower left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def report(result: dict) -> str:
    """Markdown report of the removal curves and what they say about the price of a long connection."""
    graph, sampling, baseline = result["graph"], result["sampling"], result["baseline"]
    comparison = result["comparison"]
    at, half = comparison["at_reference"], comparison["wire_share_to_halve_efficiency"]
    lost = comparison["efficiency_lost_per_metre"]
    reference = comparison["reference_wire_fraction"]

    def table(name: str) -> list[str]:
        frame = pd.DataFrame(result["curves"][name])
        columns = ["wire_removed_share", "edges_removed", "edges_removed_share", "largest_component_share",
                   "efficiency", "efficiency_share"]
        return markdown_table(frame[[c for c in columns + ["efficiency_share_sd"] if c in frame]])

    def halving(name: str) -> str:
        end = {LONGEST: "long", SHORTEST: "short"}[name]
        if half[name]:
            return f"after {half[name] * 100:.1f}% of it is taken from the {end} end"
        last = result["curves"][name][-1]
        return (f"not within the {last['wire_removed_share'] * 100:.0f}% sampled from the {end} end, where it "
                f"still stands at {last['efficiency_share'] * 100:.1f}%")

    cheaper = SHORTEST if (half[SHORTEST] or 1) < (half[LONGEST] or 1) else LONGEST
    per_edge = at[LONGEST]["efficiency_share"] < at[RANDOM]["efficiency_share"]
    ends = result["curves"][LONGEST][-1], result["curves"][SHORTEST][-1]
    lines = [
        "# What the length of a connection buys",
        "",
        f"The cell-type graph has {graph['nodes']:,} nodes, {graph['edges']:,} directed connections and "
        f"{graph['total_wire_um'] / 1e6:.2f} m of wire. Connections are removed cumulatively under three "
        "schedules and the graph that is left is measured each time: longest first, shortest first, and at "
        "random. Comparing the two ends against the same amount of wire removed answers the question the project "
        "asks — per micrometre of wire, do long connections buy more connectivity than short ones?",
        "",
        "## Measures and sampling",
        "",
        f"- **Efficiency.** The mean of 1/d over ordered pairs of nodes, d the directed shortest path in "
        f"connections. It is estimated from a fixed sample of {sampling['sources']} source nodes drawn once "
        f"(seed {sampling['source_seed']}) and used at every point of every schedule, so the curves differ only "
        "in what was removed. Characteristic path length is the more familiar measure but it is the wrong one "
        "here: removal is exactly what makes pairs unreachable, and the mean of a set that includes infinities "
        "is undefined, whereas an unreachable pair contributes a well-defined zero to efficiency. The full "
        f"distance matrix is {graph['nodes']:,} × {graph['nodes'] - 1:,} pairs per point, which is why it is "
        "sampled rather than computed whole.",
        "- **Largest component.** The number of nodes in the largest weakly connected component.",
        f"- **Sampling of the curve.** {sampling['points']} points, placed at the shares of the total wire "
        + ", ".join(f"{f:g}" for f in sampling["wire_fractions"]) + ". At each point the longest-first and "
        "shortest-first schedules have removed the same amount of wire, by construction, and the random "
        f"schedule has removed the same *number* of connections as the longest-first one. The random schedule is "
        f"the mean of {sampling['random_repeats']} draws.",
        "",
        f"The whole graph has efficiency {baseline['efficiency']:.4f} and a largest weakly connected component of "
        f"{baseline['largest_component']:,} of its {graph['nodes']:,} nodes. Every efficiency below is given as a "
        "share of that starting value.",
        "",
        "## Longest first",
        "",
        *table(LONGEST),
        "",
        "## Shortest first, matched on the wire removed",
        "",
        *table(SHORTEST),
        "",
        "## Random, matched on the number of connections removed",
        "",
        *table(RANDOM),
        "",
        "## Per micrometre of wire",
        "",
        f"At the reference point, {reference * 100:.0f}% of the wire removed "
        f"({at[LONGEST]['wire_removed_um'] / 1e6:.2f} m): taking it from the long end costs "
        f"{at[LONGEST]['edges_removed']:,} connections "
        f"({at[LONGEST]['edges_removed_share'] * 100:.1f}% of them) and leaves efficiency at "
        f"{at[LONGEST]['efficiency_share'] * 100:.1f}% of the whole graph's. Taking the same wire from the short "
        f"end costs {at[SHORTEST]['edges_removed']:,} connections "
        f"({at[SHORTEST]['edges_removed_share'] * 100:.1f}%) and leaves efficiency at "
        f"{at[SHORTEST]['efficiency_share'] * 100:.1f}%. Per metre of wire removed that is "
        f"{lost[LONGEST] * 100:.2f}% of the starting efficiency lost from the long end against "
        f"{lost[SHORTEST] * 100:.2f}% from the short end, a factor of "
        f"{lost[SHORTEST] / lost[LONGEST]:.1f}.",
        "",
        f"Efficiency falls to half its starting value {halving(SHORTEST)}, and {halving(LONGEST)}"
        + (f". The two amounts differ by a factor of {comparison['halving_wire_ratio']:.2f}"
           if "halving_wire_ratio" in comparison else "") + ".",
        "",
        "**Short connections buy more connectivity per micrometre than long ones.**" if cheaper == SHORTEST
        else "**Long connections buy more connectivity per micrometre than short ones.**",
        "",
        "The reason is arithmetic rather than subtle: a micrometre spent on short connections buys many more of "
        f"them. The median connection is {graph['median_length_um']:.0f} µm long against a mean of "
        f"{graph['mean_length_um']:.0f} µm, so the same wire taken from the short end removes "
        f"{at[SHORTEST]['edges_removed'] / max(at[LONGEST]['edges_removed'], 1):.1f} times as many connections. "
        "The budget spent on the long tail is not buying connectivity efficiently; whatever else it is for, it is "
        "not the cheapest way to keep the graph short-pathed.",
        "",
        "## Per connection",
        "",
        f"Matched on the number of connections removed rather than the wire, the picture reverses. At "
        f"{at[LONGEST]['edges_removed']:,} connections removed, taking the longest leaves efficiency at "
        f"{at[LONGEST]['efficiency_share'] * 100:.1f}% while taking the same number at random leaves it at "
        f"{at[RANDOM]['efficiency_share'] * 100:.1f}% ± {at[RANDOM]['efficiency_share_sd'] * 100:.1f}% over "
        f"{sampling['random_repeats']} draws. "
        + ("The longest connections are individually worth more to the graph than typical ones — they are simply "
           "not worth their length." if per_edge else
           "The longest connections are individually worth no more to the graph than typical ones."),
        "",
        "## Fragmentation",
        "",
        f"None of the three schedules breaks the graph apart over the range sampled. The largest weakly connected "
        f"component holds {baseline['largest_component']:,} of the {graph['nodes']:,} nodes to begin with and "
        f"still holds {at[LONGEST]['largest_component_share'] * 100:.2f}% of them after "
        f"{reference * 100:.0f}% of the wire is "
        f"taken from the long end, {at[SHORTEST]['largest_component_share'] * 100:.2f}% after the same wire is "
        f"taken from the short end and {at[RANDOM]['largest_component_share'] * 100:.2f}% after the matched number "
        f"of random removals. At the far end of the sampled range, with {ends[0]['wire_removed_share'] * 100:.0f}% "
        f"of the wire gone, the long-end schedule has cost {(1 - ends[0]['efficiency_share']) * 100:.0f}% of the "
        f"efficiency while leaving {ends[0]['largest_component_share'] * 100:.2f}% of the nodes in one component, "
        f"and the short-end schedule has cost {(1 - ends[1]['efficiency_share']) * 100:.0f}% of the efficiency "
        f"while still leaving {ends[1]['largest_component_share'] * 100:.1f}% of them in one. Component size is a "
        "blunt instrument at this density: efficiency has collapsed while the graph is still almost entirely one "
        "piece. That is a null result for the component measure rather than evidence that the graph is robust in "
        "any useful sense.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    result = tradeoff(load_spatial_graph())
    (RESULTS / "length_tradeoff.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    REPORT.write_text(report(result), encoding="utf-8")
    figure(result, RESULTS / "length_tradeoff.png")
    at = result["comparison"]["at_reference"]
    half = result["comparison"]["wire_share_to_halve_efficiency"]
    lost = result["comparison"]["efficiency_lost_per_metre"]
    print(f"Removing {REFERENCE_FRACTION * 100:.0f}% of the wire leaves efficiency at "
          f"{at[LONGEST]['efficiency_share'] * 100:.1f}% from the long end, "
          f"{at[SHORTEST]['efficiency_share'] * 100:.1f}% from the short end and "
          f"{at[RANDOM]['efficiency_share'] * 100:.1f}% at random on the matched connection count; "
          f"a metre from the short end costs {lost[SHORTEST] / lost[LONGEST]:.1f} times the efficiency a metre "
          f"from the long end does; efficiency halves at {half[SHORTEST]} of the wire from the short end and at "
          f"{half[LONGEST]} from the long")


if __name__ == "__main__":
    main()
