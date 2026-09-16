"""Physical wiring cost of a spatially embedded directed graph."""

import igraph as ig
import numpy as np


def positions_array(graph: ig.Graph) -> np.ndarray:
    """Vertex positions as an (n, 3) array from the ``x``, ``y``, ``z`` vertex attributes, in micrometers."""
    positions = np.column_stack([np.asarray(graph.vs[axis], dtype=float) for axis in "xyz"])
    if not np.isfinite(positions).all():
        raise ValueError(f"{int((~np.isfinite(positions)).any(axis=1).sum())} vertices have no finite position")
    return positions


def edge_array(graph: ig.Graph) -> np.ndarray:
    """Edge list as an (m, 2) integer array of (source, target) vertex indices."""
    return np.asarray(graph.get_edgelist(), dtype=np.int64).reshape(-1, 2)


def edge_cost(positions: np.ndarray, i: int, j: int) -> float:
    """Euclidean distance between the positions of vertices ``i`` and ``j``."""
    return float(np.linalg.norm(positions[i] - positions[j]))


def edge_costs(edges: np.ndarray, positions: np.ndarray) -> np.ndarray:
    """Euclidean length of every edge in an (m, 2) edge array."""
    return np.linalg.norm(positions[edges[:, 0]] - positions[edges[:, 1]], axis=1)


def total_wiring_cost(graph: ig.Graph, positions: np.ndarray, weighted: bool = False) -> float:
    """Sum of edge lengths over every edge of ``graph``.

    Args:
        graph: directed graph whose vertex indices index ``positions``.
        positions: (n, 3) array of vertex positions.
        weighted: multiply each edge length by its ``weight`` attribute (synapse count) before summing.

    Returns:
        Total wiring cost, in the units of ``positions`` (times synapses when weighted).
    """
    if len(positions) != graph.vcount():
        raise ValueError(f"{len(positions)} positions for {graph.vcount()} vertices")
    lengths = edge_costs(edge_array(graph), positions)
    if weighted:
        return float(np.dot(lengths, np.asarray(graph.es["weight"], dtype=float)))
    return float(lengths.sum())
