import igraph as ig
import numpy as np
import pytest

from pipeline.wiring_cost import edge_cost, edge_costs, positions_array, total_wiring_cost


def toy_graph() -> ig.Graph:
    """a(0,0,0) -> b(3,4,0) -> c(3,4,12), plus c -> a; lengths 5, 12 and 13."""
    graph = ig.Graph(directed=True)
    graph.add_vertices(["a", "b", "c"])
    graph.vs["x"] = [0.0, 3.0, 3.0]
    graph.vs["y"] = [0.0, 4.0, 4.0]
    graph.vs["z"] = [0.0, 0.0, 12.0]
    graph.add_edges([("a", "b"), ("b", "c"), ("c", "a")], attributes={"weight": [2, 1, 10]})
    return graph


def test_edge_cost_is_euclidean_distance():
    positions = positions_array(toy_graph())
    assert edge_cost(positions, 0, 1) == pytest.approx(5.0)
    assert edge_cost(positions, 1, 2) == pytest.approx(12.0)
    assert edge_cost(positions, 2, 0) == pytest.approx(13.0)
    assert edge_cost(positions, 0, 2) == edge_cost(positions, 2, 0)


def test_total_cost_matches_hand_computed_value():
    graph = toy_graph()
    positions = positions_array(graph)
    assert total_wiring_cost(graph, positions) == pytest.approx(5 + 12 + 13)
    assert total_wiring_cost(graph, positions, weighted=True) == pytest.approx(2 * 5 + 1 * 12 + 10 * 13)


def test_reciprocal_edges_are_each_paid_for():
    graph = toy_graph()
    graph.add_edges([("b", "a")], attributes={"weight": [1]})
    assert total_wiring_cost(graph, positions_array(graph)) == pytest.approx(30 + 5)


def test_vectorized_costs_agree_with_single_edge_cost():
    rng = np.random.default_rng(0)
    positions = rng.normal(size=(50, 3)) * 100
    edges = rng.integers(0, 50, size=(400, 2))
    expected = [edge_cost(positions, i, j) for i, j in edges]
    assert edge_costs(edges, positions) == pytest.approx(expected)


def test_moving_a_vertex_changes_only_its_edges():
    graph = toy_graph()
    positions = positions_array(graph)
    moved = positions.copy()
    moved[1] = [0.0, 0.0, 0.0]
    # a-b becomes 0, b-c becomes 13, c-a unchanged at 13.
    assert total_wiring_cost(graph, moved) == pytest.approx(0 + 13 + 13)


def test_graph_without_edges_costs_nothing():
    graph = toy_graph()
    graph.delete_edges(graph.es)
    assert total_wiring_cost(graph, positions_array(graph)) == 0.0


def test_missing_positions_and_size_mismatch_are_rejected():
    graph = toy_graph()
    graph.vs[1]["x"] = float("nan")
    with pytest.raises(ValueError, match="no finite position"):
        positions_array(graph)
    with pytest.raises(ValueError, match="positions for"):
        total_wiring_cost(toy_graph(), np.zeros((2, 3)))
