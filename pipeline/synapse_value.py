"""What the wire buys: synapses per micrometre of connection, across the range of connection lengths."""

import json

import igraph as ig
import numpy as np
import pandas as pd
from scipy import stats

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, markdown_table
from pipeline.connective_richclub import node_sets
from pipeline.connective_value import neck_crossing_mask
from pipeline.figures import CONNECTIVE, MUTED, NULL, REAL, apply_style, plt
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

DECILES = 10
FLAT = 0.1
GROUPS = ("all", "across the neck", "elsewhere")
REPORT = RESULTS / "synapse_value.md"


def decile_index(lengths: np.ndarray, deciles: int = DECILES) -> np.ndarray:
    """Equal-count bin of every length, 0 for the shortest bin and ``deciles - 1`` for the longest."""
    edges = np.quantile(lengths, np.linspace(0, 1, deciles + 1))
    return np.clip(np.searchsorted(edges, lengths, side="right") - 1, 0, deciles - 1)


def decile_table(lengths: np.ndarray, synapses: np.ndarray, deciles: int = DECILES) -> list[dict]:
    """Synapse count and synapses per micrometre of wire within each length decile, shortest first.

    Args:
        lengths: connection lengths in micrometers.
        synapses: synapse count of the same connections.
        deciles: number of equal-count bins.

    Returns:
        One row per bin holding its length range, its wire, its synapses, the synapses it carries per
        micrometre, and the density the bin would carry if synapse count did not depend on length.
    """
    index = decile_index(lengths, deciles)
    overall = float(synapses.mean())
    rows = []
    for b in range(deciles):
        members = index == b
        if not members.any():
            continue
        length, synapse = lengths[members], synapses[members]
        expected = overall / float(length.mean())
        observed = float(synapse.sum() / length.sum())
        rows.append({
            "decile": b + 1,
            "edges": int(members.sum()),
            "min_length_um": round(float(length.min()), 2),
            "max_length_um": round(float(length.max()), 2),
            "mean_length_um": round(float(length.mean()), 2),
            "synapses": int(synapse.sum()),
            "mean_synapses": round(float(synapse.mean()), 1),
            "median_synapses": round(float(np.median(synapse)), 1),
            "synapses_per_um": round(observed, 4),
            "expected_per_um": round(expected, 4),
            "observed_over_expected": round(observed / expected, 3),
        })
    return rows


def correlate(lengths: np.ndarray, synapses: np.ndarray) -> dict:
    """Spearman rho between length and synapse count, and Pearson r on the logarithm of both."""
    rho = stats.spearmanr(lengths, synapses)
    r = stats.pearsonr(np.log10(lengths), np.log10(synapses))
    return {
        "spearman_rho": round(float(rho.statistic), 4),
        "spearman_p": round(float(rho.pvalue), 6),
        "pearson_log_r": round(float(r.statistic), 4),
        "pearson_log_p": round(float(r.pvalue), 6),
    }


def group_summary(lengths: np.ndarray, synapses: np.ndarray) -> dict:
    """Totals, correlation and per-decile table for one set of connections."""
    deciles = decile_table(lengths, synapses)
    return {
        "edges": int(len(lengths)),
        "wire_um": round(float(lengths.sum()), 1),
        "synapses": int(synapses.sum()),
        "synapses_per_um": round(float(synapses.sum() / lengths.sum()), 4),
        "mean_synapses": round(float(synapses.mean()), 1),
        "median_synapses": round(float(np.median(synapses)), 1),
        "mean_length_um": round(float(lengths.mean()), 2),
        "correlation": correlate(lengths, synapses),
        "deciles": deciles,
        "longest_over_shortest_per_um": round(deciles[-1]["synapses_per_um"] / deciles[0]["synapses_per_um"], 6),
        "longest_over_shortest_median": round(deciles[-1]["median_synapses"] / deciles[0]["median_synapses"], 6),
    }


def synapse_value(graph: ig.Graph) -> dict:
    """Synapses bought per micrometre of wire, whole graph and split by whether a connection crosses the neck."""
    positions = positions_array(graph)
    edges = edge_array(graph)
    lengths = edge_costs(edges, positions)
    synapses = np.asarray(graph.es["weight"], dtype=float)
    crossing = neck_crossing_mask(edges, node_sets(graph))
    masks = {"all": np.ones(len(edges), dtype=bool), "across the neck": crossing, "elsewhere": ~crossing}
    return {
        "groups": {name: group_summary(lengths[mask], synapses[mask]) for name, mask in masks.items()},
        "totals": {
            "edges": int(len(edges)),
            "wire_um": round(float(lengths.sum()), 1),
            "synapses": int(synapses.sum()),
            "deciles": DECILES,
        },
    }


def figure(result: dict, path) -> None:
    """Synapses bought per micrometre across length deciles, and the synapse count behind it."""
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.8))
    colors = {"all": REAL, "across the neck": CONNECTIVE, "elsewhere": NULL}

    for name in GROUPS:
        rows = result["groups"][name]["deciles"]
        axes[0].plot([r["mean_length_um"] for r in rows], [r["synapses_per_um"] for r in rows],
                     color=colors[name], marker="o", markersize=4, label=name)
    whole = result["groups"]["all"]["deciles"]
    axes[0].plot([r["mean_length_um"] for r in whole], [r["expected_per_um"] for r in whole],
                 color=MUTED, linestyle="--", linewidth=1.2, label="if synapses did not depend on length")
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("mean connection length of the decile (µm)")
    axes[0].set_ylabel("synapses per µm of wire")
    axes[0].legend(loc="lower left")
    axes[0].set_title("The longest wire buys the fewest synapses per micrometre", loc="left", fontsize=10.5)

    y = np.arange(1, len(whole) + 1)
    axes[1].plot([r["median_synapses"] for r in whole], y, color=REAL, marker="o", markersize=4, label="median")
    axes[1].plot([r["mean_synapses"] for r in whole], y, color=MUTED, marker="s", markersize=3.5, label="mean")
    axes[1].set_yticks(y, [f"{r['min_length_um']:.0f}–{r['max_length_um']:.0f}" for r in whole], fontsize=8)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("synapses per connection")
    axes[1].set_ylabel("length decile (µm)")
    axes[1].legend(loc="upper right")
    median = [r["median_synapses"] for r in whole]
    axes[1].set_title(f"A median of {min(median):.0f}–{max(median):.0f} synapses in every decile",
                      loc="left", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def verdict(rho: float) -> str:
    """Plain wording for what a rank correlation between length and synapse count says about long connections."""
    if abs(rho) < FLAT:
        return "about the same number of synapses as short ones"
    return "fewer synapses than short ones" if rho < 0 else "more synapses than short ones"


def report(result: dict) -> str:
    """Markdown report of the per-decile synapse density and the length-against-weight correlation."""
    totals = result["totals"]
    whole = result["groups"]["all"]
    crossing, rest = result["groups"]["across the neck"], result["groups"]["elsewhere"]
    rho = whole["correlation"]["spearman_rho"]
    shortest, longest = whole["deciles"][0], whole["deciles"][-1]
    lines = [
        "# What the wire buys",
        "",
        f"The {totals['edges']:,} connections of the cell-type graph hold "
        f"{totals['wire_um'] / 1e6:.2f} m of wire and {totals['synapses']:,} synapses, "
        f"{whole['synapses_per_um']:.3f} synapses per micrometre overall. Sorted by length into deciles, the "
        f"shortest tenth buys {shortest['synapses_per_um']:.2f} synapses per micrometre and the longest tenth "
        f"{longest['synapses_per_um']:.2f}, a factor of "
        f"{shortest['synapses_per_um'] / longest['synapses_per_um']:.0f}. "
        + ("That fall is almost entirely the length in the denominator: the rank correlation"
           if abs(rho) < FLAT else "Behind it, the rank correlation")
        + f" between a connection's length and the number of synapses it carries is {rho:+.3f}, so a long "
        f"connection carries {verdict(rho)}.",
        "",
        "## Synapses per micrometre by length decile",
        "",
        *markdown_table(pd.DataFrame(whole["deciles"])),
        "",
        f"`expected_per_um` is the mean synapse count over all {totals['edges']:,} connections divided by the "
        "decile's mean length, the density the decile would show if synapse count did not depend on length at "
        "all; `observed_over_expected` is the observed density against it. A decile that buys its synapses at "
        "the going rate sits at 1.",
        "",
        "## Length against synapse count",
        "",
        *markdown_table(pd.DataFrame([{"group": name, "edges": g["edges"], "wire_um": g["wire_um"],
                                       "synapses": g["synapses"], "synapses_per_um": g["synapses_per_um"],
                                       "mean_synapses": g["mean_synapses"],
                                       "median_synapses": g["median_synapses"], **g["correlation"]}
                                      for name, g in result["groups"].items()])),
        "",
        f"This is a null result and it carries the section. Length and synapse count are all but "
        f"uncorrelated: rho = {rho:+.3f} over {whole['edges']:,} connections, and "
        f"{whole['correlation']['pearson_log_r']:+.3f} for Pearson's r on the logarithm of both. With this many "
        f"connections a correlation this small still returns a p-value at the floor of double precision, which "
        f"is a statement about the sample size and not about the size of the effect. The median connection "
        f"carries {shortest['median_synapses']:.0f} synapses in the shortest decile and "
        f"{longest['median_synapses']:.0f} in the longest, a ratio of "
        f"{whole['longest_over_shortest_median']:.2f}. Nothing here says that a connection which cost more to "
        f"build carries a heavier synaptic load; what the extra wire buys is reach, not weight.",
        "",
        "## Across the neck against everywhere else",
        "",
        f"Neck-crossing connections are the longest in the graph, mean {crossing['mean_length_um']:.0f} µm "
        f"against {rest['mean_length_um']:.0f} µm elsewhere. They hold "
        f"{crossing['wire_um'] / totals['wire_um'] * 100:.1f}% of the wire and "
        f"{crossing['synapses'] / totals['synapses'] * 100:.1f}% of the synapses, so they buy "
        f"{crossing['synapses_per_um']:.3f} synapses per micrometre against "
        f"{rest['synapses_per_um']:.3f} elsewhere, a factor of "
        f"{rest['synapses_per_um'] / crossing['synapses_per_um']:.1f} worse. Per connection, though, they carry "
        f"a median of {crossing['median_synapses']:.0f} synapses against "
        f"{rest['median_synapses']:.0f} elsewhere. Within the neck-crossing connections themselves the "
        f"correlation between length and synapse count is "
        f"{crossing['correlation']['spearman_rho']:+.3f}, against "
        f"{rest['correlation']['spearman_rho']:+.3f} for everything else. "
        + ("Both are negligible, so inside each group as well as across the whole graph the price per "
           "micrometre is set by the length and not by what the connection carries."
           if max(abs(crossing["correlation"]["spearman_rho"]), abs(rest["correlation"]["spearman_rho"])) < FLAT
           else "At least one group shows a relationship between length and synapse count worth reporting on "
                "its own."),
        "",
        "## Reading",
        "",
        ("Synapses per micrometre is a ratio whose numerator is flat and whose denominator spans the length "
         "distribution, so its decline with length is close to arithmetic rather than a discovered "
         "relationship. The finding worth stating is the flat numerator. A cell type pays for reach by the "
         "micrometre and receives, for each connection it makes, a synaptic contact of much the same size "
         "wherever the partner sits. Long connections here are not compensated with extra synapses for their "
         "cost."
         if abs(rho) < FLAT else
         "Synapses per micrometre falls with length faster than length alone accounts for, because the "
         "synapse count itself moves with length. Both terms of the ratio carry part of the decline."),
        "",
        "![What the wire buys](synapse_value.png)",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    result = synapse_value(load_spatial_graph())
    (RESULTS / "synapse_value.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    REPORT.write_text(report(result), encoding="utf-8")
    figure(result, RESULTS / "synapse_value.png")
    whole = result["groups"]["all"]
    print(f"{whole['synapses_per_um']:.3f} synapses per um overall; shortest decile "
          f"{whole['deciles'][0]['synapses_per_um']:.2f} against {whole['deciles'][-1]['synapses_per_um']:.2f} "
          f"in the longest; length against synapse count rho {whole['correlation']['spearman_rho']:+.3f}")


if __name__ == "__main__":
    main()
