import igraph as ig
import numpy as np
import pytest

from pipeline.spatial_permutation_test import permutation_null, permuted_positions, summarize, wiring_cost_of
from pipeline.wiring_cost import edge_array, positions_array, total_wiring_cost


def sorted_rows(array: np.ndarray) -> np.ndarray:
    return array[np.lexsort(array.T[::-1])]


@pytest.fixture
def positions() -> np.ndarray:
    return np.random.default_rng(11).normal(size=(300, 3)) * 100


def test_permutation_keeps_the_exact_multiset_of_positions(positions):
    shuffled = permuted_positions(positions, np.random.default_rng(1))
    np.testing.assert_array_equal(sorted_rows(shuffled), sorted_rows(positions))
    assert not np.array_equal(shuffled, positions)


def test_permutation_does_not_modify_its_input_or_the_graph(positions):
    before = positions.copy()
    graph = ig.Graph.Erdos_Renyi(n=300, m=1500, directed=True, loops=False)
    edges_before = graph.get_edgelist()
    edges = edge_array(graph)
    permutation_null(edges, positions, n_permutations=5, seed=3)
    np.testing.assert_array_equal(positions, before)
    assert graph.get_edgelist() == edges_before
    np.testing.assert_array_equal(edges, np.asarray(edges_before))


def test_group_permutation_never_moves_a_position_across_groups(positions):
    groups = np.array(["brain"] * 200 + ["vnc"] * 90 + ["unclassified"] * 10)
    shuffled = permuted_positions(positions, np.random.default_rng(2), groups)
    for label in np.unique(groups):
        members = groups == label
        np.testing.assert_array_equal(sorted_rows(shuffled[members]), sorted_rows(positions[members]))
    assert not np.array_equal(shuffled[groups == "brain"], positions[groups == "brain"])
    with pytest.raises(ValueError, match="group labels"):
        permuted_positions(positions, np.random.default_rng(2), groups[:10])


def test_null_is_reproducible_for_a_seed(positions):
    edges = np.random.default_rng(5).integers(0, 300, size=(1000, 2))
    a = permutation_null(edges, positions, 20, seed=9)
    np.testing.assert_array_equal(a, permutation_null(edges, positions, 20, seed=9))
    assert not np.array_equal(a, permutation_null(edges, positions, 20, seed=10))


def test_cost_matches_the_graph_level_wiring_cost():
    graph = ig.Graph.Erdos_Renyi(n=40, m=200, directed=True, loops=False)
    rng = np.random.default_rng(4)
    for axis in "xyz":
        graph.vs[axis] = rng.normal(size=40).tolist()
    graph.es["weight"] = rng.integers(1, 50, graph.ecount()).tolist()
    positions, edges = positions_array(graph), edge_array(graph)
    assert wiring_cost_of(edges, positions) == pytest.approx(total_wiring_cost(graph, positions))
    weights = np.asarray(graph.es["weight"], dtype=float)
    assert wiring_cost_of(edges, positions, weights) == pytest.approx(total_wiring_cost(graph, positions, weighted=True))


def test_a_chain_laid_out_in_order_is_detected_as_cheaper_than_permutations():
    # Path 0 -> 1 -> ... -> 49 with each node one unit further along x: cost 49, the minimum possible.
    n = 50
    positions = np.column_stack([np.arange(n, dtype=float), np.zeros(n), np.zeros(n)])
    edges = np.column_stack([np.arange(n - 1), np.arange(1, n)])
    real = wiring_cost_of(edges, positions)
    assert real == pytest.approx(n - 1)
    result = summarize(real, permutation_null(edges, positions, 200, seed=0))
    assert result["p_value"] == pytest.approx(1 / 201)
    assert result["z_score"] < 0
    assert result["cost_ratio"] < 1
    assert result["significant"]


def test_a_random_layout_is_not_detected_as_optimal():
    rng = np.random.default_rng(8)
    positions = rng.normal(size=(200, 3))
    edges = rng.integers(0, 200, size=(800, 2))
    null = permutation_null(edges, positions, 300, seed=1)
    real = wiring_cost_of(edges, positions)
    assert summarize(real, null)["p_value"] > 0.01
