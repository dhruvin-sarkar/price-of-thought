import igraph as ig
import numpy as np
import pytest

from pipeline.wiring_cost import edge_costs
from pipeline.wiring_economy_extensions import (
    distance_histograms,
    edge_betweenness,
    exponential_fit,
    greedy_swaps,
    neighbour_lists,
    swap_delta,
)


def random_layout(n=60, m=400, seed=0):
    rng = np.random.default_rng(seed)
    graph = ig.Graph.Erdos_Renyi(n=n, m=m, directed=True, loops=False)
    return np.asarray(graph.get_edgelist()), rng.uniform(0, 300, size=(n, 3)), graph


def test_swap_delta_matches_recomputed_cost():
    edges, positions, _ = random_layout()
    offsets, neighbours = neighbour_lists(edges, len(positions))
    before = edge_costs(edges, positions).sum()
    for i, j in [(0, 1), (5, 40), (17, 18)]:
        swapped = positions.copy()
        swapped[[i, j]] = swapped[[j, i]]
        expected = edge_costs(edges, swapped).sum() - before
        assert swap_delta(positions, offsets, neighbours, i, j) == pytest.approx(expected, abs=1e-8)


def test_greedy_swaps_never_increase_cost_and_respect_groups():
    edges, positions, _ = random_layout()
    groups = np.array(["a"] * 30 + ["b"] * 30)
    movable = np.ones(60, bool)
    movable[:5] = False
    result = greedy_swaps(positions, edges, groups, movable, 5000, seed=1, record_every=1000)
    assert result["final_cost"] <= result["start_cost"]
    assert result["tracking_error"] < 1e-9
    reductions = [r for _, r in result["trajectory"]]
    assert reductions == sorted(reductions)


def test_distance_histograms_count_every_ordered_pair_and_edge():
    edges, positions, _ = random_layout(n=40, m=200)
    brain = np.arange(40) < 25
    dist = distance_histograms(positions, brain, edges, bin_um=25.0)
    assert dist["pairs"]["all"].sum() == 40 * 39
    assert dist["pairs"]["brain-brain"].sum() == 25 * 24
    assert dist["pairs"]["vnc-vnc"].sum() == 15 * 14
    assert dist["pairs"]["cross"].sum() == 2 * 25 * 15
    assert dist["edges"]["all"].sum() == 200
    assert sum(dist["edges"][c].sum() for c in ("brain-brain", "vnc-vnc", "cross")) == 200


def test_exponential_fit_recovers_length_constant():
    d = np.arange(10, 600, 20.0)
    fit = exponential_fit(d, 0.2 * np.exp(-d / 85.0))
    assert fit["length_constant_um"] == pytest.approx(85.0, rel=1e-4)
    assert fit["a"] == pytest.approx(0.2, rel=1e-4)


def test_parallel_edge_betweenness_matches_igraph():
    _, _, graph = random_layout(n=50, m=300, seed=3)
    expected = np.asarray(graph.edge_betweenness(directed=True))
    assert edge_betweenness(graph, n_workers=2) == pytest.approx(expected)
