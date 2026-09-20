"""Attribute the wiring of the cell-type graph to the neuropils its connections run between."""

import json

import igraph as ig
import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial import cKDTree

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, SEED, markdown_table
from pipeline.figures import CONNECTIVE, INK_SECONDARY, MUTED, REAL, apply_style, plt
from pipeline.hero_render import load_all_meshes, simplify
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

MESH_CELL_NM = 3000.0
PERMUTATIONS = 1000
MIN_TYPES = 12
MIN_INTERNAL_EDGES = 50
REPORT = RESULTS / "wire_atlas.md"


def neuropil_index() -> tuple[cKDTree, list[str], np.ndarray]:
    """A search tree over every neuropil surface, with the neuropil each vertex belongs to.

    Returns:
        The tree over vertices in micrometers, the neuropil names, and the name index per vertex.
    """
    meshes = load_all_meshes()
    points, labels = [], []
    for i, (vertices, faces) in enumerate(meshes.values()):
        reduced, _ = simplify(vertices, faces, MESH_CELL_NM)
        points.append(reduced)
        labels.append(np.full(len(reduced), i))
    return cKDTree(np.concatenate(points) / 1000.0), list(meshes), np.concatenate(labels)


def assign(positions: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Nearest neuropil to each position, and the distance to that neuropil's surface in micrometers.

    A point inside a neuropil is enclosed by its surface, so the nearest surface is its own except where a
    neighbour intrudes; a point in a tract between neuropils takes the neuropil it lies closest to.
    """
    tree, names, labels = neuropil_index()
    distance, vertex = tree.query(positions, workers=-1)
    return labels[vertex], distance, names


def permuted_internal_cost(positions: np.ndarray, internal: np.ndarray, members: np.ndarray,
                           seed: int) -> np.ndarray:
    """Cost of one neuropil's internal edges under permutations of which of its members sits where."""
    index = {node: i for i, node in enumerate(members)}
    local = np.array([[index[a], index[b]] for a, b in internal])
    home = positions[members]
    rng = np.random.default_rng(seed)
    out = np.empty(PERMUTATIONS)
    for i in range(PERMUTATIONS):
        shuffled = home[rng.permutation(len(home))]
        out[i] = np.linalg.norm(shuffled[local[:, 0]] - shuffled[local[:, 1]], axis=1).sum()
    return out


def atlas(graph: ig.Graph) -> dict:
    """Wire and placement economy per neuropil, and the wire running between each pair of neuropils."""
    positions = positions_array(graph)
    edges = edge_array(graph)
    lengths = edge_costs(edges, positions)
    where, distance, names = assign(positions)
    compartment = np.asarray(graph.vs["compartment"], dtype=object)
    total_wire = float(lengths.sum())

    # Each connection lends half its length to the neuropil at each of its ends.
    wire = np.zeros(len(names))
    np.add.at(wire, where[edges[:, 0]], lengths / 2)
    np.add.at(wire, where[edges[:, 1]], lengths / 2)
    incident = np.zeros(len(names), dtype=int)
    np.add.at(incident, where[edges[:, 0]], 1)
    np.add.at(incident, where[edges[:, 1]], 1)

    rows = []
    for i, name in enumerate(names):
        members = np.flatnonzero(where == i)
        if len(members) == 0:
            continue
        row = {
            "neuropil": name,
            "compartment": "vnc" if (compartment[members] == "vnc").mean() >= 0.5 else "brain",
            "types": int(len(members)),
            "edges_incident": int(incident[i]),
            "wire_um": round(float(wire[i]), 1),
            "wire_share": round(float(wire[i] / total_wire), 6),
            "median_distance_to_surface_um": round(float(np.median(distance[members])), 2),
        }
        internal = edges[np.isin(edges[:, 0], members) & np.isin(edges[:, 1], members)]
        row["edges_internal"] = int(len(internal))
        if len(members) >= MIN_TYPES and len(internal) >= MIN_INTERNAL_EDGES:
            real = float(edge_costs(internal, positions).sum())
            null = permuted_internal_cost(positions, internal, members, SEED + i)
            row |= {
                "internal_real_um": round(real, 1),
                "internal_null_mean_um": round(float(null.mean()), 1),
                "internal_null_sd_um": round(float(null.std(ddof=1)), 1),
                "cost_ratio": round(real / float(null.mean()), 4),
                "z_score": round(float((real - null.mean()) / null.std(ddof=1)), 2),
                "n_at_or_below_real": int((null <= real).sum()),
            }
        rows.append(row)
    rows.sort(key=lambda r: -r["wire_um"])

    pair_wire: dict[tuple[int, int], list[float]] = {}
    for (a, b), length in zip(where[edges], lengths):
        key = (int(min(a, b)), int(max(a, b)))
        bucket = pair_wire.setdefault(key, [0.0, 0])
        bucket[0] += float(length)
        bucket[1] += 1
    pairs = [{"a": names[a], "b": names[b], "wire_um": round(w, 1), "edges": int(n)}
             for (a, b), (w, n) in pair_wire.items()]
    pairs.sort(key=lambda p: -p["wire_um"])

    same = where[edges[:, 0]] == where[edges[:, 1]]
    return {
        "neuropils": rows,
        "pairs": pairs[:40],
        "totals": {
            "neuropils_with_types": len(rows),
            "meshes": len(names),
            "total_wire_um": round(total_wire, 1),
            "wire_within_one_neuropil_um": round(float(lengths[same].sum()), 1),
            "share_within_one_neuropil": round(float(lengths[same].sum() / total_wire), 4),
            "edges_within_one_neuropil": int(same.sum()),
            "permutations": PERMUTATIONS,
            "median_distance_to_surface_um": round(float(np.median(distance)), 2),
        },
    }


def figure(result: dict, path) -> None:
    """Wire held by the twelve neuropils that hold most of it, and how economically each is wired internally."""
    apply_style()
    rows = result["neuropils"][:12][::-1]
    priced = [r for r in result["neuropils"] if "cost_ratio" in r]
    priced.sort(key=lambda r: r["cost_ratio"])
    priced = priced[:12][::-1]

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.2))
    y = np.arange(len(rows))
    axes[0].barh(y, [r["wire_share"] * 100 for r in rows],
                 color=[CONNECTIVE if r["compartment"] == "vnc" else REAL for r in rows], height=0.62)
    axes[0].set_yticks(y, [r["neuropil"] for r in rows], fontsize=8.5)
    axes[0].set_xlabel("share of all wire (%)")
    axes[0].set_title("Where the wire ends", loc="left", fontsize=10.5)
    for i, r in enumerate(rows):
        axes[0].text(r["wire_share"] * 100 + 0.06, i, f"{r['wire_share'] * 100:.2f}", va="center", fontsize=8,
                     color=INK_SECONDARY)

    y = np.arange(len(priced))
    axes[1].barh(y, [r["cost_ratio"] for r in priced], color=REAL, height=0.62)
    axes[1].axvline(1.0, color=MUTED, linestyle="--", linewidth=1)
    axes[1].set_yticks(y, [r["neuropil"] for r in priced], fontsize=8.5)
    axes[1].set_xlabel("internal wire / permuted mean")
    axes[1].set_xlim(0, 1.15)
    axes[1].set_title("Most economical neuropils", loc="left", fontsize=10.5)
    for i, r in enumerate(priced):
        axes[1].text(r["cost_ratio"] + 0.012, i, f"{r['cost_ratio']:.3f}", va="center", fontsize=8,
                     color=INK_SECONDARY)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def report(result: dict) -> str:
    """Markdown report of the wire held by each neuropil and its internal placement test."""
    totals = result["totals"]
    frame = pd.DataFrame(result["neuropils"])[
        ["neuropil", "compartment", "types", "edges_incident", "wire_um", "wire_share", "edges_internal",
         "cost_ratio", "z_score", "n_at_or_below_real"]
    ]
    pairs = pd.DataFrame(result["pairs"][:20])
    lines = [
        "# Wire atlas",
        "",
        f"Every cell type is assigned to the nearest of {totals['meshes']} published neuropil surfaces, and each "
        f"connection lends half its length to the neuropil at each of its ends. The median distance from a cell "
        f"type to its neuropil's surface is {totals['median_distance_to_surface_um']:.2f} µm. "
        f"{totals['share_within_one_neuropil'] * 100:.1f}% of the wire "
        f"({totals['edges_within_one_neuropil']:,} connections) stays inside one neuropil.",
        "",
        "## Wire by neuropil",
        "",
        *markdown_table(frame),
        "",
        f"`cost_ratio` is the summed length of a neuropil's internal connections against the mean of "
        f"{totals['permutations']} permutations of which of its own cell types sits at which of its own positions. "
        f"It is reported for neuropils with at least {MIN_TYPES} cell types and {MIN_INTERNAL_EDGES} internal "
        f"connections.",
        "",
        "## Wire between neuropils",
        "",
        *markdown_table(pairs),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    graph = load_spatial_graph()
    result = atlas(graph)
    (RESULTS / "wire_atlas.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    REPORT.write_text(report(result), encoding="utf-8")
    figure(result, RESULTS / "wire_atlas.png")
    top = result["neuropils"][0]
    print(f"{result['totals']['neuropils_with_types']} neuropils hold cell types; "
          f"{top['neuropil']} holds the most wire at {top['wire_share'] * 100:.2f}%; "
          f"{result['totals']['share_within_one_neuropil'] * 100:.1f}% of wire stays inside one neuropil")


if __name__ == "__main__":
    main()
