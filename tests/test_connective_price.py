import numpy as np
import pytest

from pipeline.connective_price import crossing_edges_by_node, partial_spearman


def test_crossing_edges_grouped_by_connective_endpoint():
    # Nodes 2 and 3 are connective; edge 4 is not neck-crossing.
    edges = np.array([[0, 2], [2, 1], [1, 3], [3, 0], [0, 1], [1, 2]])
    crossing = np.array([True, True, True, True, False, True])
    connective = np.array([False, False, True, True])
    grouped = crossing_edges_by_node(edges, crossing, connective)
    assert {k: v.tolist() for k, v in grouped.items()} == {2: [0, 1, 5], 3: [2, 3]}


def test_crossing_edge_between_connective_nodes_is_rejected():
    with pytest.raises(ValueError):
        crossing_edges_by_node(np.array([[0, 1]]), np.array([True]), np.array([True, True]))


def test_partial_spearman_removes_a_shared_driver():
    rng = np.random.default_rng(0)
    z = rng.normal(size=2000)
    x, y = z + rng.normal(size=2000), z + rng.normal(size=2000)
    assert abs(partial_spearman(x, y, z)[0]) < 0.05
    rho, p = partial_spearman(x + y, y, z)
    assert rho > 0.5 and p < 1e-10
