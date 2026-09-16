"""Test whether the real placement of cell types lowers total wiring cost relative to permuted placements."""

import argparse
import json

import numpy as np
import pandas as pd

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, SEED
from pipeline.figures import INK_SECONDARY, MUTED, NULL, REAL, apply_style, plt
from pipeline.rewiring import empirical_p_value_lower
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

N_PERMUTATIONS = 1000
PERMUTATION_SEED_OFFSET = 300_000
ALPHA = 0.05
PREREGISTRATION_COMMIT = "39892c5"
REPORT = RESULTS / "spatial_optimality.md"
VARIANTS = {
    "primary": "Soma positions, unweighted cost, all nodes permuted (primary)",
    "weighted": "Synapse-weighted cost",
    "within_compartment": "Permutation within compartment",
    "synapse_positions": "Synapse-centroid positions",
}


def permuted_positions(positions: np.ndarray, rng: np.random.Generator, groups: np.ndarray | None = None) -> np.ndarray:
    """Reassign the rows of ``positions`` to vertices uniformly at random.

    Args:
        positions: (n, 3) array, row i is vertex i's position.
        rng: random generator.
        groups: optional length-n labels; positions are then only exchanged between vertices with the same label.

    Returns:
        A new (n, 3) array holding the same multiset of rows (within each group, when given).
    """
    if groups is None:
        return positions[rng.permutation(len(positions))]
    groups = np.asarray(groups)
    if len(groups) != len(positions):
        raise ValueError(f"{len(groups)} group labels for {len(positions)} positions")
    shuffled = positions.copy()
    for label in np.unique(groups):
        members = np.flatnonzero(groups == label)
        shuffled[members] = positions[rng.permutation(members)]
    return shuffled


def wiring_cost_of(edges: np.ndarray, positions: np.ndarray, weights: np.ndarray | None = None) -> float:
    """Total edge length, optionally weighted, for an (m, 2) edge array and (n, 3) positions."""
    lengths = edge_costs(edges, positions)
    return float(lengths.sum() if weights is None else np.dot(lengths, weights))


def permutation_null(
    edges: np.ndarray,
    positions: np.ndarray,
    n_permutations: int,
    seed: int,
    groups: np.ndarray | None = None,
    weights: np.ndarray | None = None,
) -> np.ndarray:
    """Total wiring cost of the fixed edge set under ``n_permutations`` random position assignments."""
    rng = np.random.default_rng(seed)
    return np.array(
        [wiring_cost_of(edges, permuted_positions(positions, rng, groups), weights) for _ in range(n_permutations)]
    )


def summarize(real: float, null: np.ndarray) -> dict:
    """One-sided (real < null) comparison of a real cost with its permutation distribution."""
    sd = float(null.std(ddof=1))
    p = empirical_p_value_lower(real, null)
    return {
        "real": real,
        "null_mean": float(null.mean()),
        "null_sd": sd,
        "null_min": float(null.min()),
        "null_max": float(null.max()),
        "n_permutations": len(null),
        "n_at_or_below_real": int(np.sum(null <= real)),
        "z_score": float((real - null.mean()) / sd),
        "cost_ratio": float(real / null.mean()),
        "p_value": p,
        "significant": p < ALPHA,
    }


def synapse_positions(graph) -> np.ndarray:
    """Synapse-centroid positions of every vertex, as an (n, 3) array."""
    positions = np.column_stack([np.asarray(graph.vs[f"synapse_{axis}"], dtype=float) for axis in "xyz"])
    if not np.isfinite(positions).all():
        raise ValueError(f"{int((~np.isfinite(positions)).any(axis=1).sum())} vertices have no synapse centroid")
    return positions


def compartment_groups(graph) -> np.ndarray:
    return np.array([c if isinstance(c, str) else "unclassified" for c in graph.vs["compartment"]])


def plot(summaries: dict, nulls: dict) -> None:
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.2), dpi=200)
    for ax, (key, label) in zip(axes.flat, VARIANTS.items()):
        s, values = summaries[key], nulls[key]
        scale = 1e6 if key != "weighted" else 1e9
        unit = "m" if key != "weighted" else "km × synapses"
        lo, hi = min(values.min(), s["real"]) / scale, max(values.max(), s["real"]) / scale
        pad = 0.05 * (hi - lo)
        ax.hist(values / scale, bins=40, color=NULL, alpha=0.6, edgecolor="none",
                label=f"permuted placements (n={len(values)})")
        ax.axvline(s["real"] / scale, color=REAL, linewidth=2, label="real placement")
        ax.set_xlim(lo - pad, hi + pad)
        ax.set_title(label, loc="left")
        ax.set_xlabel(f"total wiring cost ({unit})")
        ax.text(0.5, 0.95, f"p = {s['p_value']:.4f}\nz = {s['z_score']:.1f}\nreal / permuted = {s['cost_ratio']:.3f}",
                transform=ax.transAxes, ha="center", va="top", fontsize=8.5, color=INK_SECONDARY)
        ax.grid(axis="x", visible=False)
        ax.legend(loc="upper left", fontsize=7.5)
    for ax in axes[:, 0]:
        ax.set_ylabel("permutations")
    fig.text(0.01, 0.005, "One-sided empirical p = (1 + #permutations with cost <= real) / (1 + N).",
             fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(RESULTS / "spatial_optimality.png")
    plt.close(fig)


def hypothesis_section() -> str:
    """The pre-registered hypothesis, read back from the committed report so it is never rewritten."""
    text = REPORT.read_text(encoding="utf-8")
    return text.split("\n## Procedure")[0].rstrip() + "\n"


def write_report(graph, summaries: dict, edge_lengths: np.ndarray, groups: np.ndarray) -> None:
    sources = pd.Series(graph.vs["position_source"]).value_counts()
    group_sizes = pd.Series(groups).value_counts()
    lines = [
        hypothesis_section(),
        "## Procedure",
        "",
        f"The hypothesis above was committed in `{PREREGISTRATION_COMMIT}` before the spatial graph was built.",
        "",
        f"- Graph: {graph.vcount():,} (cell type, hemisphere) nodes and {graph.ecount():,} directed edges. "
        f"{int(sources.get('soma', 0)):,} nodes are placed at their soma centroid and {int(sources.get('synapse', 0)):,} "
        "at their synapse centroid.",
        f"- Real edge lengths: median {np.median(edge_lengths):.1f} µm, mean {edge_lengths.mean():.1f} µm, "
        f"95th percentile {np.percentile(edge_lengths, 95):.1f} µm, maximum {edge_lengths.max():.1f} µm.",
        f"- Permutations: {N_PERMUTATIONS} per analysis, seeded from {SEED + PERMUTATION_SEED_OFFSET}. Compartment "
        "groups for the within-compartment analysis: "
        + ", ".join(f"{k} {int(v):,}" for k, v in group_sizes.items()) + " nodes.",
        "",
        "## Result",
        "",
        "| analysis | real cost | permuted mean ± sd | permuted range | permutations ≤ real | z | real / permuted | p | "
        f"p < {ALPHA} |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for key, label in VARIANTS.items():
        s = summaries[key]
        unit = "µm·synapses" if key == "weighted" else "µm"
        lines.append(
            f"| {label} | {s['real']:.4g} {unit} | {s['null_mean']:.4g} ± {s['null_sd']:.3g} | "
            f"{s['null_min']:.4g} – {s['null_max']:.4g} | {s['n_at_or_below_real']} / {s['n_permutations']} | "
            f"{s['z_score']:.1f} | {s['cost_ratio']:.3f} | {s['p_value']:.4f} | {'yes' if s['significant'] else 'no'} |"
        )
    primary = summaries["primary"]
    verdict = (
        "H is supported" if primary["significant"] and primary["real"] < primary["null_mean"] else "H is not supported"
    )
    lines += [
        "",
        "## Reading",
        "",
        f"Primary analysis: the real placement costs {primary['cost_ratio']:.3f} times the mean permuted placement "
        f"(z = {primary['z_score']:.1f}, p = {primary['p_value']:.4f}; {primary['n_at_or_below_real']} of "
        f"{primary['n_permutations']} permutations at or below the real cost). {verdict}.",
        "",
    ]
    for key in ("weighted", "within_compartment", "synapse_positions"):
        s = summaries[key]
        direction = "lower than" if s["real"] < s["null_mean"] else "not lower than"
        lines.append(
            f"- {VARIANTS[key]}: real cost {direction} the permuted mean, ratio {s['cost_ratio']:.3f}, "
            f"z = {s['z_score']:.1f}, p = {s['p_value']:.4f}."
        )
    lines += [
        "",
        f"With {N_PERMUTATIONS} permutations the smallest attainable p is {1 / (N_PERMUTATIONS + 1):.4f}, so the "
        "z-score and the cost ratio carry the size of the effect. The test compares the real placement with random "
        "placements of the same positions; it does not show that the real placement is the cheapest possible one.",
        "",
        "![Permutation distributions](spatial_optimality.png)",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-permutations", type=int, default=N_PERMUTATIONS)
    args = parser.parse_args()

    graph = load_spatial_graph()
    edges = edge_array(graph)
    soma = positions_array(graph)
    synapse = synapse_positions(graph)
    weights = np.asarray(graph.es["weight"], dtype=float)
    groups = compartment_groups(graph)
    seed = SEED + PERMUTATION_SEED_OFFSET

    setups = {
        "primary": (soma, None, None),
        "weighted": (soma, None, weights),
        "within_compartment": (soma, groups, None),
        "synapse_positions": (synapse, None, None),
    }
    summaries, nulls = {}, {}
    for key, (positions, group_labels, w) in setups.items():
        real = wiring_cost_of(edges, positions, w)
        nulls[key] = permutation_null(edges, positions, args.n_permutations, seed, group_labels, w)
        summaries[key] = summarize(real, nulls[key])
        s = summaries[key]
        print(f"{key:>20}: real {s['real']:.4g}, permuted {s['null_mean']:.4g} ± {s['null_sd']:.3g}, "
              f"ratio {s['cost_ratio']:.3f}, z {s['z_score']:.1f}, p {s['p_value']:.4f}", flush=True)

    plot(summaries, nulls)
    write_report(graph, summaries, edge_costs(edges, soma), groups)
    pd.DataFrame(nulls).to_csv(RESULTS / "spatial_permutation_costs.csv", index_label="permutation", float_format="%.6g")
    (RESULTS / "spatial_optimality.json").write_text(
        json.dumps({"preregistration_commit": PREREGISTRATION_COMMIT, "seed": seed, "alpha": ALPHA,
                    "analyses": summaries}, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
