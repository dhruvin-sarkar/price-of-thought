import igraph as ig
import numpy as np
import pytest
from scipy.spatial import cKDTree

import pipeline.wire_atlas as wire_atlas
from pipeline.wire_atlas import PERMUTATIONS, assign, atlas, permuted_internal_cost


def box(center: np.ndarray, half: float) -> np.ndarray:
    """The eight corners of an axis-aligned cube, standing in for a neuropil surface."""
    offsets = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], dtype=float)
    return center + offsets * half


@pytest.fixture
def two_neuropils(monkeypatch) -> list[str]:
    """Two cubic surfaces of side 20 um whose centers sit 100 um apart on the x axis."""
    names = ["left", "right"]
    surfaces = [box(np.zeros(3), 10.0), box(np.array([100.0, 0.0, 0.0]), 10.0)]
    points = np.concatenate(surfaces)
    labels = np.concatenate([np.full(len(s), i) for i, s in enumerate(surfaces)])
    monkeypatch.setattr(wire_atlas, "neuropil_index", lambda: (cKDTree(points), names, labels))
    return names


def spatial_graph(positions: np.ndarray, compartments: list[str], edges: list[tuple[int, int]]) -> ig.Graph:
    """Directed graph carrying the position and compartment attributes the atlas reads."""
    graph = ig.Graph(n=len(positions), edges=edges, directed=True)
    for i, axis in enumerate("xyz"):
        graph.vs[axis] = positions[:, i].tolist()
    graph.vs["compartment"] = compartments
    return graph


def test_each_position_takes_the_neuropil_whose_surface_is_nearest(two_neuropils):
    positions = np.array([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [30.0, 0.0, 0.0], [70.0, 0.0, 0.0]])
    where, distance, names = assign(positions)
    assert names == two_neuropils
    assert where.tolist() == [0, 1, 0, 1]
    assert distance == pytest.approx([np.sqrt(300), np.sqrt(300), np.sqrt(600), np.sqrt(600)])


def test_permuted_internal_cost_is_reproducible_and_stays_within_the_neuropil():
    positions = np.random.default_rng(3).uniform(0, 100, size=(20, 3))
    members = np.arange(5, 15)
    internal = np.array([[5, 6], [6, 7], [7, 12], [12, 14], [5, 14]])
    null = permuted_internal_cost(positions, internal, members, seed=4)
    assert len(null) == PERMUTATIONS
    assert (null > 0).all()
    # No permutation can stretch an edge beyond the widest separation of the neuropil's own positions.
    spread = np.linalg.norm(positions[members][:, None] - positions[members][None], axis=2).max()
    assert null.max() <= len(internal) * spread
    np.testing.assert_array_equal(null, permuted_internal_cost(positions, internal, members, seed=4))
    assert not np.array_equal(null, permuted_internal_cost(positions, internal, members, seed=5))


def test_a_connection_lends_half_its_length_to_the_neuropil_at_each_end(two_neuropils):
    positions = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 4.0], [0.0, 3.0, 0.0],
                          [100.0, 0.0, 0.0], [100.0, 0.0, 6.0]])
    graph = spatial_graph(positions, ["brain"] * 3 + ["vnc"] * 2, [(0, 1), (1, 2), (0, 3), (3, 4)])
    # Lengths of 4, 5 and 6 um inside a neuropil and 100 um between the two.
    result = atlas(graph)
    left, right = result["neuropils"]

    assert (left["neuropil"], right["neuropil"]) == ("left", "right")
    assert (left["compartment"], right["compartment"]) == ("brain", "vnc")
    assert (left["types"], right["types"]) == (3, 2)
    assert left["wire_um"] == pytest.approx(4 + 5 + 100 / 2)
    assert right["wire_um"] == pytest.approx(6 + 100 / 2)
    assert left["wire_share"] + right["wire_share"] == pytest.approx(1.0)
    assert sum(r["wire_um"] for r in result["neuropils"]) == pytest.approx(result["totals"]["total_wire_um"])
    assert (left["edges_incident"], right["edges_incident"]) == (5, 3)
    assert (left["edges_internal"], right["edges_internal"]) == (2, 1)
    assert "cost_ratio" not in left and "cost_ratio" not in right


def test_the_wire_between_neuropils_accounts_for_every_connection(two_neuropils):
    positions = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 4.0], [0.0, 3.0, 0.0],
                          [100.0, 0.0, 0.0], [100.0, 0.0, 6.0]])
    graph = spatial_graph(positions, ["brain"] * 3 + ["vnc"] * 2, [(0, 1), (1, 2), (0, 3), (3, 4)])
    result = atlas(graph)
    totals = result["totals"]

    assert totals["total_wire_um"] == pytest.approx(115.0)
    assert totals["wire_within_one_neuropil_um"] == pytest.approx(15.0)
    assert totals["share_within_one_neuropil"] == pytest.approx(15 / 115, abs=5e-5)
    assert totals["edges_within_one_neuropil"] == 3
    assert (totals["meshes"], totals["neuropils_with_types"]) == (2, 2)
    assert result["pairs"] == [
        {"a": "left", "b": "right", "wire_um": 100.0, "edges": 1},
        {"a": "left", "b": "left", "wire_um": 9.0, "edges": 2},
        {"a": "right", "b": "right", "wire_um": 6.0, "edges": 1},
    ]
    assert sum(p["wire_um"] for p in result["pairs"]) == pytest.approx(totals["total_wire_um"])
