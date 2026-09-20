"""Collapse the cell-type graph onto the neuropils and characterise the region-level network it forms."""

import json
import random
import re

import igraph as ig
import numpy as np
import pandas as pd

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, SEED, markdown_table
from pipeline.figures import CONNECTIVE, INK_SECONDARY, MUTED, NULL, REAL, SURFACE, apply_style, plt
from pipeline.wire_atlas import assign
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

N_NULLS = 1000
N_PARTITION_SEEDS = 100
HUBS = 15
NULL_SEED_OFFSET = 600_000
PARTITION_SEED_OFFSET = 650_000
ATLAS = RESULTS / "wire_atlas.json"
REPORT = RESULTS / "neuropil_network.md"


def pair_wire(where: np.ndarray, edges: np.ndarray, lengths: np.ndarray,
              n_regions: int) -> tuple[np.ndarray, np.ndarray]:
    """Wire and connection count between every ordered-by-index pair of regions.

    Args:
        where: region index of every vertex.
        edges: (m, 2) array of vertex indices.
        lengths: length of every edge, in micrometers.
        n_regions: number of regions the indices in ``where`` range over.

    Returns:
        Two symmetric (n_regions, n_regions) arrays: the wire running between each pair and the number of
        connections behind it. A connection contributes its whole length to the one pair it joins, so the
        diagonal holds the wire that stays inside a region and the matrices sum to twice the total wire off
        the diagonal plus the diagonal once.
    """
    a = np.minimum(where[edges[:, 0]], where[edges[:, 1]])
    b = np.maximum(where[edges[:, 0]], where[edges[:, 1]])
    flat = a * n_regions + b
    size = n_regions * n_regions
    upper = np.bincount(flat, weights=lengths, minlength=size).reshape(n_regions, n_regions)
    counts = np.bincount(flat, minlength=size).reshape(n_regions, n_regions).astype(np.int64)
    wire = upper + upper.T - np.diag(np.diag(upper))
    counts = counts + counts.T - np.diag(np.diag(counts))
    return wire, counts


def ranked_pairs(names: list[str], wire: np.ndarray, counts: np.ndarray, limit: int | None = None) -> list[dict]:
    """Every pair of regions holding wire, itself included, heaviest first, as `wire_atlas.json` saves them."""
    rows, n = [], len(names)
    for i in range(n):
        for j in range(i, n):
            if counts[i, j]:
                rows.append({"a": names[i], "b": names[j], "wire_um": round(float(wire[i, j]), 1),
                             "edges": int(counts[i, j])})
    rows.sort(key=lambda r: -r["wire_um"])
    return rows if limit is None else rows[:limit]


def side_of(name: str) -> str | None:
    """Hemisphere suffix of a neuropil name, ``L`` or ``R``, or None for an unpaired midline neuropil."""
    match = re.search(r"\(([LR])\)$", name)
    return match.group(1) if match else None


def segment_of(name: str) -> str | None:
    """Thoracic segment named in a neuropil name, ``T1``, ``T2`` or ``T3``, or None when it names none."""
    match = re.search(r"T([123])", name)
    return f"T{match.group(1)}" if match else None


def region_graph(names: list[str], wire: np.ndarray, counts: np.ndarray) -> ig.Graph:
    """Undirected weighted graph over the regions, one edge per pair of distinct regions holding wire.

    Vertex attributes: ``name``, ``internal_um`` and ``internal_edges`` for the wire that stays inside the
    region. Edge attributes: ``wire`` in micrometers and ``connections``.
    """
    n = len(names)
    upper = np.triu_indices(n, 1)
    present = counts[upper] > 0
    graph = ig.Graph(n=n, edges=list(zip(upper[0][present].tolist(), upper[1][present].tolist())), directed=False)
    graph.vs["name"] = names
    graph.vs["internal_um"] = np.diag(wire).tolist()
    graph.vs["internal_edges"] = np.diag(counts).astype(int).tolist()
    graph.es["wire"] = wire[upper][present].tolist()
    graph.es["connections"] = counts[upper][present].astype(int).tolist()
    return graph


def metrics(graph: ig.Graph) -> dict[str, float]:
    """Mean local clustering and characteristic path length of a region graph, unweighted and wire-weighted.

    The weighted path length measures an edge by ``max wire / its wire``, so a step along the heaviest pair of
    regions costs one and a thinner pair costs proportionally more. Regions with fewer than two partners
    contribute zero to the mean clustering.
    """
    wire = np.asarray(graph.es["wire"], dtype=float)
    cost = (wire.max() / wire).tolist()
    return {
        "clustering": float(graph.transitivity_avglocal_undirected(mode="zero")),
        "path_length": float(graph.average_path_length()),
        "weighted_clustering": float(graph.transitivity_avglocal_undirected(mode="zero", weights="wire")),
        "weighted_path_length": float(graph.average_path_length(weights=cost)),
    }


def rewired_null(graph: ig.Graph, seed: int) -> ig.Graph:
    """Degree-preserving rewiring of the region graph with the wire values dealt out again at random.

    Every region keeps its exact number of partners and the multiset of per-pair wire values is unchanged,
    but which pair of regions holds a given amount of wire is randomized, so region strength is not preserved.
    """
    null = graph.copy()
    random.seed(seed)
    null.rewire(n=10 * graph.ecount(), allowed_edge_types="simple")
    rng = np.random.default_rng(seed)
    null.es["wire"] = rng.permutation(np.asarray(graph.es["wire"], dtype=float)).tolist()
    return null


def shuffled_null(graph: ig.Graph, seed: int) -> ig.Graph:
    """The real region topology with the wire values permuted over its existing edges.

    Every region keeps its exact partners, so the unweighted structure is untouched and only the arrangement
    of wire over that structure is randomized.
    """
    null = graph.copy()
    rng = np.random.default_rng(seed)
    null.es["wire"] = rng.permutation(np.asarray(graph.es["wire"], dtype=float)).tolist()
    return null


def compare(real: float, null: np.ndarray) -> dict:
    """Two-sided empirical comparison of a real statistic with its null distribution."""
    null = np.asarray(null, dtype=float)
    above, below = int(np.sum(null >= real)), int(np.sum(null <= real))
    sd = float(null.std(ddof=1))
    return {
        "real": round(real, 4),
        "null_mean": round(float(null.mean()), 4),
        "null_sd": round(sd, 4),
        "null_lo": round(float(np.percentile(null, 2.5)), 4),
        "null_hi": round(float(np.percentile(null, 97.5)), 4),
        "ratio": round(real / float(null.mean()), 4),
        "z_score": round((real - float(null.mean())) / sd, 2) if sd > 0 else None,
        "n_at_or_above_real": above,
        "p_value": round(min(1.0, 2 * (1 + min(above, below)) / (1 + len(null))), 4),
    }


def small_world(graph: ig.Graph, n_nulls: int, seed: int) -> dict:
    """The four metrics against both degree-preserving nulls, and the small-world ratio each null implies."""
    real = metrics(graph)
    out = {"real": {k: round(v, 4) for k, v in real.items()}, "nulls": {}}
    for label, build in (("rewired", rewired_null), ("weights shuffled", shuffled_null)):
        drawn = [metrics(build(graph, seed + i)) for i in range(n_nulls)]
        comparisons = {k: compare(real[k], np.array([d[k] for d in drawn])) for k in real}
        for prefix in ("", "weighted_"):
            c, length = comparisons[f"{prefix}clustering"], comparisons[f"{prefix}path_length"]
            comparisons[f"{prefix}sigma"] = round(c["ratio"] / length["ratio"], 4)
        out["nulls"][label] = comparisons
    return out


def partition(graph: ig.Graph, seed: int) -> list[int]:
    """Louvain community membership of the wire-weighted region graph under one random seed."""
    random.seed(seed)
    return list(graph.community_multilevel(weights="wire").membership)


def stable_partition(graph: ig.Graph, n_seeds: int, seed: int) -> tuple[list[int], dict]:
    """The membership Louvain returns most often over ``n_seeds`` seeds, and how often it returns it."""
    tally: dict[tuple[int, ...], int] = {}
    for i in range(n_seeds):
        key = tuple(partition(graph, seed + i))
        tally[key] = tally.get(key, 0) + 1
    best, count = max(tally.items(), key=lambda item: item[1])
    return list(best), {"seeds": n_seeds, "distinct_partitions": len(tally), "seeds_agreeing": count}


def correspondence(membership: list[int], labels: list[str | None]) -> dict | None:
    """Agreement of a community partition with an anatomical label, over the regions carrying that label.

    Returns None when fewer than two regions carry the label. Otherwise the adjusted Rand index and the
    normalized mutual information between the two partitions of those regions.
    """
    carried = [i for i, label in enumerate(labels) if label is not None]
    if len(carried) < 2:
        return None
    codes = {label: i for i, label in enumerate(sorted({labels[i] for i in carried}))}
    truth = [codes[labels[i]] for i in carried]
    mine = [membership[i] for i in carried]
    return {
        "regions": len(carried),
        "groups": len(codes),
        "adjusted_rand": round(float(ig.compare_communities(mine, truth, method="adjusted_rand")), 4),
        "nmi": round(float(ig.compare_communities(mine, truth, method="nmi")), 4),
    }


def mirrored_pairs(names: list[str], membership: list[int]) -> dict:
    """How often a neuropil's left and right copies fall in the same community.

    Returns the number of neuropils present on both sides, the number whose two copies sit in different
    communities, and their names without the side suffix.
    """
    sides: dict[str, dict[str, int]] = {}
    for i, name in enumerate(names):
        side = side_of(name)
        if side is not None:
            sides.setdefault(name[: -len(f"({side})")], {})[side] = membership[i]
    both = {stem: found for stem, found in sides.items() if len(found) == 2}
    split = sorted(stem for stem, found in both.items() if found["L"] != found["R"])
    return {"neuropils_on_both_sides": len(both), "split_across_communities": len(split), "split": split}


def atlas_agreement(names: list[str], wire: np.ndarray, counts: np.ndarray, total: float) -> dict:
    """Check the recomputed pair matrix against the committed wire atlas, and fail loudly if it disagrees.

    The atlas saves only its top pairs, so the whole matrix is recomputed here; this confirms the two agree
    on the total wire and on every pair the atlas does save.
    """
    saved = json.loads(ATLAS.read_text(encoding="utf-8"))
    saved_total = saved["totals"]["total_wire_um"]
    if not np.isclose(total, saved_total, rtol=1e-6):
        raise ValueError(f"recomputed total wire {total:.1f} um against {saved_total:.1f} um in the atlas")
    saved_pairs = saved["pairs"]
    mine = ranked_pairs(names, wire, counts, len(saved_pairs))
    if mine != saved_pairs:
        differing = [p["a"] + "-" + p["b"] for p, q in zip(mine, saved_pairs) if p != q]
        raise ValueError(f"{len(differing)} of the atlas top pairs do not reproduce: {differing[:5]}")
    return {"total_wire_um": round(total, 1), "atlas_total_wire_um": saved_total, "pairs_reproduced": len(mine)}


def network(graph: ig.Graph) -> dict:
    """The region-level network, its hubs, its small-world comparison and its community partition."""
    positions = positions_array(graph)
    edges = edge_array(graph)
    lengths = edge_costs(edges, positions)
    where, _, mesh_names = assign(positions)
    compartment = np.asarray(graph.vs["compartment"], dtype=object)
    total_wire = float(lengths.sum())

    all_wire, all_counts = pair_wire(where, edges, lengths, len(mesh_names))
    agreement = atlas_agreement(mesh_names, all_wire, all_counts, total_wire)
    present = np.flatnonzero(np.bincount(where, minlength=len(mesh_names)))
    names = [mesh_names[i] for i in present]
    wire, counts = all_wire[np.ix_(present, present)], all_counts[np.ix_(present, present)]

    regions = region_graph(names, wire, counts)
    membership, stability = stable_partition(regions, N_PARTITION_SEEDS, SEED + PARTITION_SEED_OFFSET)
    strength = np.asarray(wire.sum(axis=1) - np.diag(wire))
    internal = np.diag(wire)
    between = float(strength.sum() / 2)

    rows, compartments = [], []
    for i, name in enumerate(names):
        members = np.flatnonzero(where == present[i])
        compartments.append("vnc" if (compartment[members] == "vnc").mean() >= 0.5 else "brain")
        rows.append({
            "neuropil": name,
            "compartment": compartments[i],
            "side": side_of(name) or "",
            "community": int(membership[i]) + 1,
            "types": int(len(members)),
            "degree": int(regions.degree(i)),
            "strength_um": round(float(strength[i]), 1),
            "strength_share": round(float(strength[i] / (2 * between)), 5),
            "internal_um": round(float(internal[i]), 1),
            # Half of the wire between two regions is credited to each, which is what the atlas records.
            "atlas_wire_um": round(float(internal[i] + strength[i] / 2), 1),
        })
    rows.sort(key=lambda r: -r["strength_um"])

    labels = {
        "compartment": compartments,
        "side": [side_of(name) for name in names],
        "segment": [segment_of(name) for name in names],
    }
    communities = []
    for community in sorted(set(membership)):
        members = [r for r in rows if r["community"] == community + 1]
        communities.append({
            "community": community + 1,
            "regions": len(members),
            "brain_regions": sum(1 for r in members if r["compartment"] == "brain"),
            "vnc_regions": sum(1 for r in members if r["compartment"] == "vnc"),
            "strength_um": round(sum(r["strength_um"] for r in members), 1),
            "members": [r["neuropil"] for r in members],
        })

    degrees = np.asarray(regions.degree())
    possible = len(names) * (len(names) - 1) // 2
    return {
        "totals": {
            "regions": len(names),
            "meshes": len(mesh_names),
            "region_edges": regions.ecount(),
            "possible_region_edges": possible,
            "density": round(regions.ecount() / possible, 4),
            "min_degree": int(degrees.min()),
            "median_degree": float(np.median(degrees)),
            "total_wire_um": round(total_wire, 1),
            "between_region_wire_um": round(between, 1),
            "within_region_wire_um": round(float(internal.sum()), 1),
            "share_between_regions": round(between / total_wire, 4),
            "n_nulls": N_NULLS,
        },
        "atlas_agreement": agreement,
        "regions": rows,
        "network": {
            "regions": names,
            "internal_um": [round(float(v), 1) for v in internal],
            "internal_edges": [int(v) for v in np.diag(counts)],
            # One row per joined pair, heaviest first: the two region indices, the wire and the connections.
            "pairs": sorted(([int(a), int(b), round(float(w), 1), int(c)] for (a, b), w, c
                             in zip(regions.get_edgelist(), regions.es["wire"], regions.es["connections"])),
                            key=lambda pair: -pair[2]),
        },
        "small_world": small_world(regions, N_NULLS, SEED + NULL_SEED_OFFSET),
        "partition": {"method": "Louvain on the wire-weighted undirected region graph",
                      "communities": len(communities),
                      "modularity": round(float(regions.modularity(membership, weights="wire")), 4),
                      **stability},
        "communities": communities,
        "anatomy": {name: correspondence(membership, label) for name, label in labels.items()},
        "mirrored": mirrored_pairs(names, membership),
    }


def figure(result: dict, path) -> None:
    """The regions holding most wire, the wire matrix ordered by community, and the small-world comparison."""
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(15.6, 5.0))

    hubs = result["regions"][:HUBS][::-1]
    y = np.arange(len(hubs))
    axes[0].barh(y, [r["strength_um"] / 1e6 for r in hubs],
                 color=[CONNECTIVE if r["compartment"] == "vnc" else REAL for r in hubs], height=0.62)
    axes[0].set_yticks(y, [r["neuropil"] for r in hubs], fontsize=8.5)
    axes[0].set_xlabel("wire to other regions (m)")
    axes[0].set_title("Hubs by wire", loc="left", fontsize=10.5)
    for i, r in enumerate(hubs):
        axes[0].text(r["strength_um"] / 1e6 + 0.12, i, f"{r['degree']} partners", va="center", fontsize=7.5,
                     color=INK_SECONDARY)
    axes[0].set_xlim(0, max(r["strength_um"] for r in hubs) / 1e6 * 1.35)

    net = result["network"]
    order, sizes = [], []
    for community in result["communities"]:
        order += community["members"]
        sizes.append(len(community["members"]))
    seat = {name: i for i, name in enumerate(order)}
    place = [seat[name] for name in net["regions"]]
    matrix = np.full((len(order), len(order)), np.nan)
    for i, j, wire, _ in net["pairs"]:
        matrix[place[i], place[j]] = matrix[place[j], place[i]] = wire
    for i, wire in enumerate(net["internal_um"]):
        if wire > 0:
            matrix[place[i], place[i]] = wire
    colors = plt.get_cmap("magma_r").copy()
    colors.set_bad(SURFACE)
    image = axes[1].imshow(np.log10(matrix), cmap=colors, interpolation="nearest")
    boundary = sizes[0] - 0.5
    for draw in (axes[1].axhline, axes[1].axvline):
        draw(boundary, color=NULL, linewidth=1.2)
    axes[1].set_xticks([])
    axes[1].set_yticks([])
    axes[1].grid(visible=False)
    axes[1].set_xlabel(f"{len(order)} regions, ordered by community")
    axes[1].set_title("Wire between regions", loc="left", fontsize=10.5)
    bar = fig.colorbar(image, ax=axes[1], fraction=0.046, pad=0.03)
    bar.set_label("log10 wire (µm)", fontsize=8.5, color=INK_SECONDARY)
    bar.ax.tick_params(labelsize=8)

    labels, ratios, lows, highs = [], [], [], []
    for null, comparisons in result["small_world"]["nulls"].items():
        for key, text in (("weighted_clustering", "clustering"), ("weighted_path_length", "path length")):
            c = comparisons[key]
            labels.append(f"{text}\nvs {null}")
            ratios.append(c["ratio"])
            lows.append(c["null_lo"] / c["null_mean"])
            highs.append(c["null_hi"] / c["null_mean"])
    y = np.arange(len(labels))[::-1]
    axes[2].hlines(y, lows, highs, color=NULL, linewidth=6, alpha=0.4, label="null, central 95%")
    axes[2].plot(ratios, y, "o", color=REAL, markersize=6, linestyle="none", label="real / null mean")
    axes[2].axvline(1.0, color=MUTED, linestyle="--", linewidth=1)
    axes[2].set_yticks(y, labels, fontsize=8)
    axes[2].set_xscale("log")
    axes[2].set_xlim(0.4, 80)
    axes[2].set_ylim(-0.7, len(labels) - 0.3)
    axes[2].set_xlabel("real relative to the null mean")
    axes[2].set_title("Wire-weighted small-world comparison", loc="left", fontsize=10.5)
    axes[2].legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def report(result: dict) -> str:
    """Markdown report of the region network, its hubs, its small-world test and its communities."""
    totals, world, part = result["totals"], result["small_world"], result["partition"]
    frame = pd.DataFrame(result["regions"])[
        ["neuropil", "compartment", "side", "community", "types", "degree", "strength_um", "strength_share",
         "internal_um", "atlas_wire_um"]
    ]

    def null_rows(label: str) -> list[str]:
        comparisons = world["nulls"][label]
        table = pd.DataFrame([
            {"metric": name.replace("_", " "), "real": comparisons[name]["real"],
             "null mean": comparisons[name]["null_mean"], "null sd": comparisons[name]["null_sd"],
             "null central 95%": f"{comparisons[name]['null_lo']:g} to {comparisons[name]['null_hi']:g}",
             "real / null": comparisons[name]["ratio"], "p": comparisons[name]["p_value"]}
            for name in ("clustering", "path_length", "weighted_clustering", "weighted_path_length")
        ])
        return markdown_table(table)

    anatomy = pd.DataFrame([
        {"anatomical split": name, "regions labelled": v["regions"], "groups": v["groups"],
         "adjusted Rand": v["adjusted_rand"], "normalized mutual information": v["nmi"]}
        for name, v in result["anatomy"].items() if v is not None
    ])
    rewired = world["nulls"]["rewired"]
    hub = result["regions"][0]
    lines = [
        "# Neuropil network",
        "",
        f"Collapsing the cell-type graph onto the neuropils gives a network of {totals['regions']} regions joined "
        f"by {totals['region_edges']:,} weighted edges, {totals['density'] * 100:.1f}% of the "
        f"{totals['possible_region_edges']:,} pairs that could be joined. Every cell type takes the nearest of "
        f"{totals['meshes']} published neuropil surfaces and each connection lends half its length to the neuropil at "
        "each of its ends, the rule `wire_atlas.py` uses; the whole pair matrix is recomputed here because the atlas "
        f"saves only its {result['atlas_agreement']['pairs_reproduced']} largest pairs. The recomputation reproduces "
        f"the atlas total of {result['atlas_agreement']['atlas_total_wire_um'] / 1e6:.2f} m and every pair it saves. "
        f"{totals['share_between_regions'] * 100:.1f}% of the wire runs between two regions and the rest stays inside "
        "one.",
        "",
        "## Regions",
        "",
        "`strength_um` is the wire running between a region and every other region; `internal_um` is the wire that "
        "stays inside it. A micrometre between two regions belongs to both, so `atlas_wire_um`, which halves it, is "
        "the figure `wire_atlas.md` reports and the strengths sum to twice the between-region wire.",
        "",
        *markdown_table(frame),
        "",
        "## Hubs",
        "",
        f"{hub['neuropil']} is the largest hub by wire, holding {hub['strength_um'] / 1e6:.2f} m to "
        f"{hub['degree']} of the other {totals['regions'] - 1} regions, "
        f"{hub['strength_share'] * 100:.1f}% of all between-region wire. The "
        f"{HUBS} largest regions by wire hold "
        f"{sum(r['strength_share'] for r in result['regions'][:HUBS]) * 100:.1f}% of it between them. Degree "
        f"separates the regions much less than wire does: the median region has "
        f"{totals['median_degree']:.0f} partners and the least connected has {totals['min_degree']}.",
        "",
        "## Small-world comparison",
        "",
        f"Two nulls, {totals['n_nulls']} draws each, both of which preserve every region's number of partners "
        "exactly:",
        "",
        "- **Rewired.** Degree-preserving edge swaps randomize which pairs of regions are joined, and the multiset "
        "of per-pair wire values is then dealt out over the rewired edges at random. Region strength is not "
        "preserved.",
        "- **Weights shuffled.** The real topology is left alone and only the wire values are permuted over its "
        "edges, so the unweighted clustering and path length are the real ones by construction and the comparison "
        "isolates the arrangement of wire.",
        "",
        "Clustering is the mean local clustering coefficient and path length the mean shortest path over all pairs; "
        "the weighted versions weigh a pair by its wire, a step along the heaviest pair of regions costing one and a "
        "thinner pair proportionally more.",
        "",
        "### Against the rewired null",
        "",
        *null_rows("rewired"),
        "",
        "### Against the weight-shuffled null",
        "",
        *null_rows("weights shuffled"),
        "",
        f"The region network is more clustered than the rewired null by wire "
        f"({rewired['weighted_clustering']['ratio']:.3f} times the null mean) but its weighted paths are "
        f"{rewired['weighted_path_length']['ratio']:.1f} times longer, not shorter, which puts the wire-weighted "
        f"small-world ratio at {rewired['weighted_sigma']:.3f} — far below the one a small-world network would give. "
        "The network is not small-world by wire. The unweighted structure cannot answer the question either way: at "
        f"{totals['density'] * 100:.0f}% density almost every pair of regions is already joined, so the unweighted "
        f"clustering is {world['real']['clustering']:.3f} against a null mean of "
        f"{rewired['clustering']['null_mean']:.3f} and the mean path is "
        f"{world['real']['path_length']:.2f} steps against {rewired['path_length']['null_mean']:.2f}. The long "
        "weighted paths are the expected consequence of heavy pairs sitting together rather than bridging the "
        "network: the weight-shuffled null, which keeps the topology and moves only the wire, reproduces the same "
        f"direction at {world['nulls']['weights shuffled']['weighted_path_length']['ratio']:.1f} times the null mean.",
        "",
        "## Communities",
        "",
        f"Louvain on the wire-weighted region graph returns {part['communities']} communities with modularity "
        f"{part['modularity']:.3f}. " + (
            f"All {part['seeds']} random seeds return the same partition."
            if part["distinct_partitions"] == 1 else
            f"Over {part['seeds']} random seeds it returns {part['distinct_partitions']} distinct partitions, "
            f"{part['seeds_agreeing']} of them the one reported here."),
        "",
        *markdown_table(pd.DataFrame([{k: v for k, v in c.items() if k != "members"} for c in result["communities"]])),
        "",
    ]
    for community in result["communities"]:
        lines += [f"**Community {community['community']}** ({community['regions']} regions, largest by wire first): "
                  + ", ".join(community["members"]) + ".", ""]
    compartment = result["anatomy"]["compartment"]
    side, segment, mirror = result["anatomy"]["side"], result["anatomy"]["segment"], result["mirrored"]
    crossing = [c for c in result["communities"] if c["brain_regions"] and c["vnc_regions"]]
    mixed = crossing[0] if crossing else None
    lines += [
        "## Do the communities follow anatomy",
        "",
        *markdown_table(anatomy),
        "",
        f"The partition follows the brain and nerve cord split and nothing else. Against the compartment label it "
        f"reaches an adjusted Rand index of {compartment['adjusted_rand']:.3f} over all "
        f"{compartment['regions']} regions. Against hemisphere it reaches {side['adjusted_rand']:.3f} over the "
        f"{side['regions']} regions carrying an `(L)` or `(R)` suffix, and against thoracic segment "
        f"{segment['adjusted_rand']:.3f} over the {segment['regions']} regions naming a segment — both indices sit "
        f"at chance. Of the {mirror['neuropils_on_both_sides']} neuropils present on both sides, "
        + ("every one has its two copies in the same community" if not mirror["split"] else
           f"only {mirror['split'][0]} has its two copies in different communities"
           if len(mirror["split"]) == 1 else
           f"{mirror['split_across_communities']} have their two copies in different communities ("
           + ", ".join(mirror["split"]) + ")")
        + ", and the leg neuropils of all three thoracic segments sit together; the wire that joins a region to its "
        "mirror image or to its neighbouring segment does not separate either from the rest of its compartment.",
        "",
    ]
    if mixed is not None:
        lines += [
            f"The correspondence with the compartment is strong but not exact. Community {mixed['community']} holds "
            f"every one of the {mixed['vnc_regions']} nerve-cord neuropils together with {mixed['brain_regions']} "
            "brain neuropils — "
            + ", ".join(m for m in mixed["members"]
                        if next(r for r in result["regions"] if r["neuropil"] == m)["compartment"] == "brain")
            + " — which are the gnathal and ventral-posterior regions that sit against the neck. On wire alone they "
            "group with the nerve cord rather than with the rest of the brain.",
            "",
        ]
    return "\n".join(lines)


def main() -> None:
    result = network(load_spatial_graph())
    (RESULTS / "neuropil_network.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    REPORT.write_text(report(result), encoding="utf-8")
    figure(result, RESULTS / "neuropil_network.png")
    totals, hub = result["totals"], result["regions"][0]
    rewired = result["small_world"]["nulls"]["rewired"]
    print(f"{totals['regions']} regions, {totals['region_edges']:,} edges at density {totals['density']:.2f}; "
          f"{hub['neuropil']} is the largest hub with {hub['strength_um'] / 1e6:.2f} m of wire; weighted clustering "
          f"{rewired['weighted_clustering']['ratio']:.3f} and weighted path length "
          f"{rewired['weighted_path_length']['ratio']:.1f} times the rewired null; "
          f"{result['partition']['communities']} communities, adjusted Rand "
          f"{result['anatomy']['compartment']['adjusted_rand']:.3f} against brain versus nerve cord")


if __name__ == "__main__":
    main()
