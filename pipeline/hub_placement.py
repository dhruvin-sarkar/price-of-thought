"""Test whether heavily connected cell types sit centrally, and whether a type sits near the cells it contacts."""

import json

import igraph as ig
import numpy as np
import pandas as pd
from scipy import stats

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, SEED, markdown_table
from pipeline.figures import CONNECTIVE, INK_SECONDARY, MUTED, NULL, REAL, apply_style, plt
from pipeline.rewiring import empirical_p_value_lower
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

PERMUTATIONS = 1000
PARTNER_SEED_OFFSET = 100_000
BINS = 10
EXTREMES = 12
SCOPES = ("all", "brain", "nerve cord")
REPORT = RESULTS / "hub_placement.md"


def degree_and_wire(edges: np.ndarray, lengths: np.ndarray, n_vertices: int) -> tuple[np.ndarray, np.ndarray]:
    """Total degree and summed incident connection length of every vertex.

    Args:
        edges: (m, 2) array of vertex indices.
        lengths: length of each edge, in micrometers.
        n_vertices: number of vertices.

    Returns:
        The degree of every vertex and the wire of the connections it takes part in.
    """
    degree = np.bincount(edges[:, 0], minlength=n_vertices) + np.bincount(edges[:, 1], minlength=n_vertices)
    wire = np.zeros(n_vertices)
    np.add.at(wire, edges[:, 0], lengths)
    np.add.at(wire, edges[:, 1], lengths)
    return degree, wire


def distance_to_centroid(positions: np.ndarray) -> np.ndarray:
    """Distance from each of the positions given to their common centroid, in their own units."""
    return np.linalg.norm(positions - positions.mean(axis=0), axis=1)


def correlate(values: np.ndarray, distance: np.ndarray) -> dict:
    """Rank and log correlation of a per-type quantity with distance from the centre.

    Args:
        values: non-negative per-type quantity, such as degree or wire.
        distance: distance from the centroid, one per type.

    Returns:
        Spearman rho over every type, and Pearson r on the base-10 logarithm of the positive values.
    """
    rho = stats.spearmanr(values, distance)
    positive = values > 0
    r = stats.pearsonr(np.log10(values[positive]), distance[positive])
    return {
        "spearman_rho": round(float(rho.statistic), 4),
        "spearman_p": round(float(rho.pvalue), 6),
        "pearson_log_r": round(float(r.statistic), 4),
        "pearson_log_p": round(float(r.pvalue), 6),
    }


def binned(values: np.ndarray, distance: np.ndarray, bins: int = BINS) -> list[dict]:
    """Median distance from the centre within each equal-count bin of ``values``, lowest bin first."""
    edges = np.quantile(values, np.linspace(0, 1, bins + 1))
    index = np.clip(np.searchsorted(edges, values, side="right") - 1, 0, bins - 1)
    rows = []
    for b in range(bins):
        members = index == b
        if not members.any():
            continue
        rows.append({
            "bin": b + 1,
            "types": int(members.sum()),
            "median_value": round(float(np.median(values[members])), 2),
            "median_distance_um": round(float(np.median(distance[members])), 2),
        })
    return rows


def partner_distance(edges: np.ndarray, positions: np.ndarray, degree: np.ndarray) -> np.ndarray:
    """Distance from every vertex to the centroid of its partners' positions; NaN where a vertex has none.

    A partner counts once per connection, so a pair joined in both directions is weighted twice.
    """
    total = np.zeros_like(positions)
    np.add.at(total, edges[:, 0], positions[edges[:, 1]])
    np.add.at(total, edges[:, 1], positions[edges[:, 0]])
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.linalg.norm(positions - total / degree[:, None], axis=1)


def random_partner_distance(positions: np.ndarray, index: np.ndarray, degree: np.ndarray,
                            rng: np.random.Generator) -> np.ndarray:
    """One draw of the null: each listed vertex keeps its degree but takes partners at random.

    Args:
        positions: (n, 3) positions of every vertex.
        index: indices of the vertices to draw partners for, each with a degree of at least one.
        degree: number of partners to draw for each listed vertex.
        rng: random generator.

    Returns:
        Distance from each listed vertex to the centroid of the partners it drew.
    """
    owner = np.repeat(index, degree)
    draws = rng.integers(0, len(positions) - 1, size=len(owner))
    draws += draws >= owner  # skip the vertex itself, so no type is ever its own partner
    starts = np.concatenate(([0], np.cumsum(degree)[:-1]))
    centroids = np.add.reduceat(positions[draws], starts, axis=0) / degree[:, None]
    return np.linalg.norm(positions[index] - centroids, axis=1)


def compare(real: float, null: np.ndarray) -> dict:
    """One-sided (real below null) comparison of a mean distance with its permutation distribution."""
    sd = float(null.std(ddof=1))
    return {
        "real_um": round(real, 2),
        "null_mean_um": round(float(null.mean()), 2),
        "null_sd_um": round(sd, 3),
        "z_score": round((real - float(null.mean())) / sd, 1),
        "ratio": round(real / float(null.mean()), 4),
        "n_at_or_below_real": int((null <= real).sum()),
        "p_value": round(empirical_p_value_lower(real, null), 6),
        "permutations": len(null),
    }


def partner_test(positions: np.ndarray, edges: np.ndarray, degree: np.ndarray, masks: dict[str, np.ndarray],
                 seed: int, permutations: int = PERMUTATIONS) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    """Compare each type's distance to its partners' centroid with random partners of the same number.

    Args:
        positions: (n, 3) positions of every vertex.
        edges: (m, 2) array of vertex indices.
        degree: total degree of every vertex.
        masks: boolean vertex masks, one per scope, summarized separately.
        seed: seed of the random generator.
        permutations: number of random partner draws.

    Returns:
        The per-scope comparison, the indices of the vertices tested, their real distances, and their
        z-scores against their own null distribution.
    """
    index = np.flatnonzero(degree > 0)
    real = partner_distance(edges, positions, degree)[index]
    rng = np.random.default_rng(seed)
    scope_null = {name: np.empty(permutations) for name in masks}
    total = np.zeros(len(index))
    total_square = np.zeros(len(index))
    for i in range(permutations):
        drawn = random_partner_distance(positions, index, degree[index], rng)
        for name, mask in masks.items():
            scope_null[name][i] = drawn[mask[index]].mean()
        total += drawn
        total_square += drawn**2
    mean = total / permutations
    sd = np.sqrt(np.maximum(total_square / permutations - mean**2, 0) * permutations / (permutations - 1))
    scopes = {name: compare(float(real[mask[index]].mean()), scope_null[name]) for name, mask in masks.items()}
    return scopes, index, real, (real - mean) / sd


def hub_placement(graph: ig.Graph) -> dict:
    """Degree against distance from the centre, and each type's distance to the centroid of its partners."""
    positions = positions_array(graph)
    edges = edge_array(graph)
    lengths = edge_costs(edges, positions)
    degree, wire = degree_and_wire(edges, lengths, graph.vcount())
    compartment = np.asarray(graph.vs["compartment"], dtype=object)
    cell_type = np.asarray(graph.vs["cell_type"], dtype=object)
    side = np.asarray(graph.vs["side"], dtype=object)
    masks = {"all": np.ones(graph.vcount(), dtype=bool), "brain": compartment == "brain",
             "nerve cord": compartment == "vnc"}

    scopes, correlations, bins = [], [], []
    for scope in SCOPES:
        members = masks[scope]
        distance = distance_to_centroid(positions[members])
        centroid = positions[members].mean(axis=0)
        scopes.append({
            "scope": scope,
            "types": int(members.sum()),
            "centroid_um": [round(float(v), 1) for v in centroid],
            "median_distance_um": round(float(np.median(distance)), 2),
            "max_distance_um": round(float(distance.max()), 2),
        })
        for measure, values in (("degree", degree[members].astype(float)), ("wire", wire[members])):
            correlations.append({"scope": scope, "measure": measure, "types": int(members.sum()),
                                 **correlate(values, distance)})
            if measure == "degree":
                bins += [{"scope": scope, **row} for row in binned(values, distance)]

    seed = SEED + PARTNER_SEED_OFFSET
    partners, index, real, z_score = partner_test(positions, edges, degree, masks, seed)
    order = np.argsort(z_score)[:EXTREMES]
    extremes = [{
        "cell_type": str(cell_type[index[i]]),
        "side": str(side[index[i]]),
        "compartment": str(compartment[index[i]]),
        "degree": int(degree[index[i]]),
        "distance_to_partners_um": round(float(real[i]), 2),
        "z_score": round(float(z_score[i]), 1),
    } for i in order]

    return {
        "scopes": scopes,
        "correlations": correlations,
        "degree_bins": bins,
        "partners": {
            "scopes": partners,
            "types_tested": int(len(index)),
            "share_nearer_than_chance": round(float((z_score < 0).mean()), 4),
            "seed": seed,
            "extremes": extremes,
        },
        "totals": {
            "types": graph.vcount(),
            "isolated_types": int((degree == 0).sum()),
            "connections": graph.ecount(),
            "permutations": PERMUTATIONS,
        },
    }


def figure(result: dict, path) -> None:
    """Distance from the centre across degree bins, and the partner-centroid distance against its null."""
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.8))

    colors = {"all": REAL, "brain": NULL, "nerve cord": CONNECTIVE}
    for scope in SCOPES:
        rows = [r for r in result["degree_bins"] if r["scope"] == scope]
        axes[0].plot([r["bin"] for r in rows], [r["median_distance_um"] for r in rows],
                     color=colors[scope], marker="o", markersize=4, label=scope)
    axes[0].set_xlabel("degree bin (tenth of the cell types, least connected first)")
    axes[0].set_ylabel("median distance from the centroid (µm)")
    axes[0].set_xticks(range(1, BINS + 1))
    axes[0].set_ylim(bottom=0)
    axes[0].legend(loc="lower left")
    axes[0].set_title("Hubs sit no closer to the centre", loc="left", fontsize=10.5)

    partners = result["partners"]["scopes"]
    y = np.arange(len(partners))[::-1]
    axes[1].barh(y + 0.19, [s["null_mean_um"] for s in partners.values()], color=NULL, height=0.34,
                 label=f"partners drawn at random (n={next(iter(partners.values()))['permutations']})")
    axes[1].barh(y - 0.19, [s["real_um"] for s in partners.values()], color=REAL, height=0.34,
                 label="the partners a type actually has")
    axes[1].set_yticks(y, list(partners), fontsize=9)
    axes[1].set_xlabel("mean distance to the centroid of a type's partners (µm)")
    axes[1].set_xlim(0, max(s["null_mean_um"] for s in partners.values()) * 1.32)
    axes[1].legend(loc="lower right")
    for i, summary in zip(y, partners.values()):
        axes[1].text(summary["null_mean_um"] + 6, i + 0.19, f"{summary['null_mean_um']:.0f}", va="center",
                     fontsize=8, color=MUTED)
        axes[1].text(summary["real_um"] + 6, i - 0.19, f"{summary['real_um']:.0f} µm, "
                     f"{summary['ratio']:.2f}× chance", va="center", fontsize=8, color=INK_SECONDARY)
    axes[1].set_title("Types sit close to the cells they contact", loc="left", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def direction(rho: float) -> str:
    """Plain wording for the sign and size of a rank correlation with distance from the centre."""
    if abs(rho) < 0.1:
        return "no relationship"
    strength = "a weak" if abs(rho) < 0.3 else "a moderate" if abs(rho) < 0.5 else "a strong"
    return (f"{strength} tendency for the better connected types to sit closer to the centre" if rho < 0
            else f"{strength} tendency for the better connected types to sit further out")


def report(result: dict) -> str:
    """Markdown report of the centrality correlations and the partner-centroid permutation test."""
    totals = result["totals"]
    degree_rho = {r["scope"]: r for r in result["correlations"] if r["measure"] == "degree"}
    whole, partners = degree_rho["all"], result["partners"]
    brain, cord = degree_rho["brain"], degree_rho["nerve cord"]
    agree = (brain["spearman_rho"] < 0) == (cord["spearman_rho"] < 0)
    largest = max(result["correlations"], key=lambda r: abs(r["spearman_rho"]))
    bound = abs(largest["spearman_rho"])
    lines = [
        "# Hub placement",
        "",
        f"A cell type that is heavily connected pays its position on every one of its connections, so wiring "
        f"economy predicts that the best connected types sit centrally. Over all {totals['types']:,} cell types "
        f"the rank correlation between total degree and distance from the centroid of every type's position is "
        f"{whole['spearman_rho']:+.3f}: {direction(whole['spearman_rho'])}. Split by compartment it is "
        f"{brain['spearman_rho']:+.3f} in the brain and {cord['spearman_rho']:+.3f} in the nerve cord, which "
        f"{'agree in sign' if agree else 'do not even agree in sign'}.",
        "",
        "## Where the types sit",
        "",
        *markdown_table(pd.DataFrame([{**r, "centroid_um": ", ".join(f"{v:g}" for v in r["centroid_um"])}
                                      for r in result["scopes"]])),
        "",
        "Distance is measured from the centroid of the cell types of that scope, not of the whole specimen: the "
        "brain and the nerve cord occupy different volumes, and a shared centre would rank a type by which "
        "compartment it belongs to rather than by where it sits inside it.",
        "",
        "## Degree and wire against distance from the centre",
        "",
        *markdown_table(pd.DataFrame(result["correlations"])),
        "",
        "`spearman_rho` is over every type in the scope; `pearson_log_r` is Pearson's r between the base-10 "
        f"logarithm of the measure and the distance, over the types with a positive value "
        f"({totals['isolated_types']} of {totals['types']:,} types have no connection at all). `degree` is a "
        "type's total degree and `wire` is the summed length of the connections it takes part in.",
        "",
        f"The largest correlation in the table is {largest['spearman_rho']:+.3f}, for {largest['measure']} in the "
        f"{largest['scope']} scope; every other one is smaller in absolute value. The brain and the "
        f"nerve cord {'lean the same way' if agree else 'lean opposite ways'}, which is why they are reported "
        f"apart: pooling them would have {'compounded' if agree else 'cancelled'} two weak tendencies into one "
        f"number that belongs to neither compartment. "
        + ("This is a null result: at the level of whole cell types, how well connected a type is says next to "
           "nothing about how far from the centre of its compartment it sits."
           if bound < 0.3 else
           "The relationship is weak but consistent enough to be worth reporting as a real one."),
        "",
        "## Distance to one's own partners",
        "",
        f"The same cell types are, however, placed close to the cells they actually contact. Each type is "
        f"compared with a null in which it keeps its degree but draws that many partners uniformly at random "
        f"from the other cell types, never itself, with replacement; {partners['scopes']['all']['permutations']} "
        f"draws, seeded from {partners['seed']}.",
        "",
        *markdown_table(pd.DataFrame([{"scope": k, **v} for k, v in partners["scopes"].items()])),
        "",
        f"Over the {partners['types_tested']:,} types with at least one connection the mean distance to the "
        f"centroid of a type's partners is {partners['scopes']['all']['real_um']:.1f} µm against "
        f"{partners['scopes']['all']['null_mean_um']:.1f} µm for random partners, a ratio of "
        f"{partners['scopes']['all']['ratio']:.3f} "
        f"(z = {partners['scopes']['all']['z_score']:.1f}, p = {partners['scopes']['all']['p_value']:.4f}). "
        f"{partners['share_nearer_than_chance'] * 100:.1f}% of types sit nearer their own partners than their "
        f"own null mean.",
        "",
        "The types furthest below their own null, in units of that null's standard deviation:",
        "",
        *markdown_table(pd.DataFrame(partners["extremes"])),
        "",
        ("Taken together the two tests say that placement economy here is local rather than radial. A type is "
         "placed among its partners, but being well connected does not pull it towards the middle of its "
         "compartment."
         if partners["scopes"]["all"]["ratio"] < 1 and bound < 0.3 else
         "The two tests are reported side by side because they measure different things: distance from a fixed "
         "centre, and distance from the cells a type is wired to."),
        "",
        "![Hub placement](hub_placement.png)",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    result = hub_placement(load_spatial_graph())
    (RESULTS / "hub_placement.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    REPORT.write_text(report(result), encoding="utf-8")
    figure(result, RESULTS / "hub_placement.png")
    whole = next(r for r in result["correlations"] if r["scope"] == "all" and r["measure"] == "degree")
    partners = result["partners"]["scopes"]["all"]
    print(f"degree against distance from the centre: rho {whole['spearman_rho']:+.3f} overall; "
          f"partner-centroid distance {partners['real_um']:.1f} um against {partners['null_mean_um']:.1f} um "
          f"for random partners (ratio {partners['ratio']:.3f}, p {partners['p_value']:.4f})")


if __name__ == "__main__":
    main()
