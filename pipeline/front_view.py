"""Record the hero image's front view as vectors: the CNS silhouette and a fixed sample of neck-crossing wires."""

import json

import contourpy
import numpy as np
from scipy import ndimage

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import RESULTS, SEED
from pipeline.connective_richclub import node_sets
from pipeline.connective_value import neck_crossing_mask
from pipeline.hero_render import CLUSTER_NM, LENGTH_RANGE_UM, PITCH, YAW, load_all_meshes, project, rotation, simplify
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

OUT = RESULTS / "front_view.json"
GRID_UM = 4.0
N_WIRES = 3000
SAMPLE_SEED_OFFSET = 950_000


def silhouette(points: np.ndarray, grid: float = GRID_UM, close_cells: int = 3) -> list[np.ndarray]:
    """Outer outlines of a dense 2D point cloud, traced on an occupancy grid.

    Parameters: ``points`` is an (n, 2) array of screen coordinates in µm; ``grid`` the cell size in µm;
    ``close_cells`` the radius, in cells, of the morphological closing that bridges gaps between points.
    Returns each closed outline as an (m, 2) array in the same coordinates, largest first.
    """
    lo = points.min(axis=0) - (close_cells + 2) * grid
    index = np.floor((points - lo) / grid).astype(int)
    shape = index.max(axis=0) + close_cells + 3
    occupied = np.zeros(shape[::-1], dtype=bool)
    occupied[index[:, 1], index[:, 0]] = True
    structure = ndimage.generate_binary_structure(2, 1)
    filled = ndimage.binary_fill_holes(ndimage.binary_closing(occupied, structure, iterations=close_cells))
    lines = contourpy.contour_generator(z=filled.astype(float)).lines(0.5)
    outlines = [line * grid + lo for line in lines if len(line) > 8]
    return sorted(outlines, key=lambda o: -np.ptp(o[:, 0]) * np.ptp(o[:, 1]))


def wire_sample(n_total: int, n: int, seed: int) -> np.ndarray:
    """Sorted indices of ``n`` of ``n_total`` wires drawn uniformly without replacement."""
    return np.sort(np.random.default_rng(seed).choice(n_total, size=min(n, n_total), replace=False))


def main() -> None:
    graph = load_spatial_graph()
    edges = edge_array(graph)
    positions = positions_array(graph)
    crossing = np.flatnonzero(neck_crossing_mask(edges, node_sets(graph)))
    lengths = edge_costs(edges, positions)[crossing]

    view = rotation(PITCH, YAW)
    meshes = load_all_meshes()
    vertices = np.concatenate([simplify(v, f, CLUSTER_NM)[0] for v, f in meshes.values()])
    center = vertices.mean(axis=0)
    shell = project(vertices, center, view) / 1000.0
    outlines = silhouette(shell)

    chosen = wire_sample(len(crossing), N_WIRES, SEED + SAMPLE_SEED_OFFSET)
    ends = project(positions[edges[crossing[chosen]]] * 1000.0, center, view) / 1000.0
    order = np.argsort(lengths[chosen], kind="stable")
    bounds = np.concatenate(outlines)
    summary = {
        "view": {"pitch_deg": PITCH, "yaw_deg": YAW, "units": "µm, x right, y up"},
        "bounds": {"min": bounds.min(axis=0).round(1).tolist(), "max": bounds.max(axis=0).round(1).tolist()},
        "length_range_um": list(LENGTH_RANGE_UM),
        "crossing_edges": int(len(crossing)),
        "sample": {"n": int(len(chosen)), "seed_offset": SAMPLE_SEED_OFFSET},
        "outlines": [o.round(1).tolist() for o in outlines],
        "wires": [[*ends[i, 0].round(1).tolist(), *ends[i, 1].round(1).tolist(), round(float(lengths[chosen][i]), 1)]
                  for i in order],
    }
    OUT.write_text(json.dumps(summary, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(outlines)} outlines, {len(chosen):,} of {len(crossing):,} wires, {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
