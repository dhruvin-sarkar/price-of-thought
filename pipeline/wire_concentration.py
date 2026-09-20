"""How unevenly the wiring budget is spread over connections and over the classes of cell that own them."""

import json

import numpy as np
import pandas as pd
import powerlaw

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, markdown_table
from pipeline.connective_richclub import node_sets
from pipeline.connective_value import neck_crossing_mask
from pipeline.figures import CONNECTIVE, INK_SECONDARY, MUTED, NULL, REAL, SURFACE, apply_style, plt
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

CURVE_POINTS = 400
TOP_SHARES = (0.001, 0.01, 0.05, 0.10, 0.25, 0.50)
REPORT = RESULTS / "wire_concentration.md"


def lorenz(lengths: np.ndarray, points: int = CURVE_POINTS) -> dict:
    """Cumulative share of wire against cumulative share of connections, longest first, with its Gini.

    Args:
        lengths: connection lengths in micrometers.
        points: how many points to keep on the curve.

    Returns:
        The curve, the Gini coefficient, and the wire share held by the longest few percent.
    """
    descending = np.sort(lengths)[::-1]
    cumulative = np.cumsum(descending) / descending.sum()
    fraction = np.arange(1, len(descending) + 1) / len(descending)
    keep = np.unique(np.linspace(0, len(descending) - 1, points).astype(int))
    ascending = np.cumsum(np.sort(lengths)) / lengths.sum()
    gini = 1 - 2 * float(np.trapezoid(ascending, dx=1 / len(ascending)))
    return {
        "connection_share": [round(float(v), 6) for v in fraction[keep]],
        "wire_share": [round(float(v), 6) for v in cumulative[keep]],
        "gini": round(gini, 4),
        "top_shares": {f"{s:g}": round(float(cumulative[max(0, int(s * len(descending)) - 1)]), 4)
                       for s in TOP_SHARES},
        "connections": int(len(lengths)),
    }


def summary(lengths: np.ndarray) -> dict:
    """Count, total, mean, median and upper quantiles of a set of connection lengths."""
    return {
        "edges": int(len(lengths)),
        "wire_um": round(float(lengths.sum()), 1),
        "mean_um": round(float(lengths.mean()), 2),
        "median_um": round(float(np.median(lengths)), 2),
        "p90_um": round(float(np.quantile(lengths, 0.9)), 2),
        "p99_um": round(float(np.quantile(lengths, 0.99)), 2),
        "max_um": round(float(lengths.max()), 2),
    }


def tail(lengths: np.ndarray) -> dict:
    """Fit a power law to the upper tail of the length distribution and weigh it against three alternatives.

    Lengths are rounded to the micrometer before fitting. The search for the lower bound tries every distinct
    value, and rounding takes that from half a million candidates to about a thousand without moving the fit
    by more than the rounding itself.

    Returns:
        The fitted lower bound and exponent, and the normalized log-likelihood ratio and p-value against each
        alternative. A positive ratio favors the power law.
    """
    fit = powerlaw.Fit(np.round(lengths), verbose=False)
    out = {"xmin_um": round(float(fit.xmin), 2), "alpha": round(float(fit.alpha), 3),
           "tail_edges": int((lengths >= fit.xmin).sum()), "comparisons": {}}
    for other in ("lognormal", "exponential", "truncated_power_law"):
        ratio, p = fit.distribution_compare("power_law", other, normalized_ratio=True)
        out["comparisons"][other] = {"loglikelihood_ratio": round(float(ratio), 3), "p_value": round(float(p), 4)}
    return out


def concentration(graph) -> dict:
    """Length summaries, the Lorenz curve of wire, its tail, and the wire owned by each superclass."""
    positions = positions_array(graph)
    edges = edge_array(graph)
    lengths = edge_costs(edges, positions)
    sets = node_sets(graph)
    crossing = neck_crossing_mask(edges, sets)
    compartment = np.asarray(graph.vs["compartment"], dtype=object)
    superclass = np.asarray(graph.vs["superclass"], dtype=object)
    total = float(lengths.sum())

    both = compartment[edges]
    groups = {
        "all": np.ones(len(edges), dtype=bool),
        "within the brain": (both[:, 0] == "brain") & (both[:, 1] == "brain"),
        "within the nerve cord": (both[:, 0] == "vnc") & (both[:, 1] == "vnc"),
        "across the neck": crossing,
    }

    rows = []
    for name, superclass_mask in [(s, superclass == s) for s in pd.unique(superclass)]:
        touching = superclass_mask[edges[:, 0]] | superclass_mask[edges[:, 1]]
        if touching.sum() == 0:
            continue
        # A connection between two types of the same class is counted once for that class.
        rows.append({
            "superclass": name,
            "types": int(superclass_mask.sum()),
            "edges": int(touching.sum()),
            "wire_um": round(float(lengths[touching].sum()), 1),
            "wire_share": round(float(lengths[touching].sum() / total), 5),
            "mean_length_um": round(float(lengths[touching].mean()), 2),
            "median_length_um": round(float(np.median(lengths[touching])), 2),
        })
    rows.sort(key=lambda r: -r["wire_um"])

    return {
        "lengths": {name: summary(lengths[mask]) for name, mask in groups.items() if mask.sum()},
        "lorenz": {name: lorenz(lengths[mask]) for name, mask in groups.items() if mask.sum() > 100},
        "tail": tail(lengths),
        "superclasses": rows,
        "total_wire_um": round(total, 1),
    }


def figure(result: dict, path) -> None:
    """The Lorenz curve of wire against connections, and the length distribution behind it."""
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.8))

    colors = {"all": REAL, "within the brain": NULL, "within the nerve cord": MUTED, "across the neck": CONNECTIVE}
    for name, curve in result["lorenz"].items():
        axes[0].plot(np.array(curve["connection_share"]) * 100, np.array(curve["wire_share"]) * 100,
                     color=colors.get(name, REAL), linewidth=2, label=f"{name} (G = {curve['gini']:.2f})")
    axes[0].plot([0, 100], [0, 100], color=MUTED, linestyle="--", linewidth=1)
    axes[0].set_xlabel("longest connections (%)")
    axes[0].set_ylabel("share of all wire (%)")
    axes[0].set_xlim(0, 100)
    axes[0].set_ylim(0, 100)
    axes[0].legend(frameon=False, fontsize=8.5, loc="lower right")
    axes[0].set_title("A tenth of the connections hold a third of the wire", loc="left", fontsize=10.5)

    top = result["lorenz"]["all"]["top_shares"]
    for share in ("0.01", "0.1"):
        if share in top:
            axes[0].plot([float(share) * 100], [top[share] * 100], "o", color=REAL, markersize=5)
            axes[0].annotate(f"{top[share] * 100:.0f}%", (float(share) * 100, top[share] * 100),
                             textcoords="offset points", xytext=(8, -3), fontsize=8.5, color=INK_SECONDARY)

    lengths = result["lengths"]
    names = [n for n in ("within the brain", "within the nerve cord", "across the neck") if n in lengths]
    y = np.arange(len(names))
    axes[1].barh(y, [lengths[n]["mean_um"] for n in names],
                 color=[colors[n] for n in names], height=0.5)
    for i, n in enumerate(names):
        axes[1].plot([lengths[n]["median_um"]], [i], "|", color=SURFACE, markersize=16, markeredgewidth=2)
        axes[1].text(lengths[n]["mean_um"] + 8, i, f"mean {lengths[n]['mean_um']:.0f}, "
                     f"median {lengths[n]['median_um']:.0f} µm", va="center", fontsize=8.5, color=INK_SECONDARY)
    axes[1].set_yticks(y, names, fontsize=9)
    axes[1].set_xlabel("connection length (µm)")
    axes[1].set_xlim(0, max(lengths[n]["mean_um"] for n in names) * 1.9)
    axes[1].set_title("Mean and median length, by where a connection runs", loc="left", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def report(result: dict) -> str:
    """Markdown report of the length distribution, the concentration of wire and the per-class budget."""
    curve = result["lorenz"]["all"]
    tail_fit = result["tail"]
    lines = [
        "# Wire concentration",
        "",
        f"The {curve['connections']:,} connections of the cell-type graph hold "
        f"{result['total_wire_um'] / 1e6:.2f} m of wire between them. Sorted longest first, the top 1% hold "
        f"{curve['top_shares']['0.01'] * 100:.1f}% of it and the top 10% hold "
        f"{curve['top_shares']['0.1'] * 100:.1f}%; the Gini coefficient of the length distribution is "
        f"{curve['gini']:.3f}.",
        "",
        "## Length by where a connection runs",
        "",
        *markdown_table(pd.DataFrame([{"group": k, **v} for k, v in result["lengths"].items()])),
        "",
        "## Concentration",
        "",
        *markdown_table(pd.DataFrame([{"group": k, "gini": v["gini"],
                                       **{f"top {float(s) * 100:g}%": v["top_shares"][s] for s in v["top_shares"]}}
                                      for k, v in result["lorenz"].items()])),
        "",
        "## Upper tail",
        "",
        f"A power law fitted above {tail_fit['xmin_um']:.0f} µm, covering {tail_fit['tail_edges']:,} connections, "
        f"has exponent {tail_fit['alpha']:.2f}. Weighed against alternatives, a positive ratio favors the power "
        "law:",
        "",
        *markdown_table(pd.DataFrame([{"against": k, **v} for k, v in tail_fit["comparisons"].items()])),
        "",
        "## Wire by superclass",
        "",
        "A connection is counted for the class of each of its two ends, so the shares sum to more than one.",
        "",
        *markdown_table(pd.DataFrame(result["superclasses"])),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    result = concentration(load_spatial_graph())
    (RESULTS / "wire_concentration.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    REPORT.write_text(report(result), encoding="utf-8")
    figure(result, RESULTS / "wire_concentration.png")
    curve = result["lorenz"]["all"]
    print(f"Gini {curve['gini']:.3f}; the longest 1% of connections hold "
          f"{curve['top_shares']['0.01'] * 100:.1f}% of the wire and the longest 10% hold "
          f"{curve['top_shares']['0.1'] * 100:.1f}%; tail exponent {result['tail']['alpha']:.2f}")


if __name__ == "__main__":
    main()
