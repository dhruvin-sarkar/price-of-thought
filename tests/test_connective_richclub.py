import igraph as ig
import numpy as np
import pytest

from pipeline.connective_richclub import (
    enrichment_null,
    layer_edges,
    partner_richness,
    randomize_layer,
    rich_club_coefficient,
    rich_edge_fraction,
    rich_mask,
    route_counts,
)


def toy():
    """Brain partners b0..b2 (0-2), nerve-cord partners v0..v2 (3-5), descending d (6), ascending a (7).

    b0 -> d, b1 -> d, d -> v0, d -> v1, d -> v2, v0 -> a, a -> b0, a -> b2, plus b0 -> b1 and v0 -> v1.
    """
    edges = np.array([[0, 6], [1, 6], [6, 3], [6, 4], [6, 5], [3, 7], [7, 0], [7, 2], [0, 1], [3, 4]])
    role = np.array(["none"] * 6 + ["descending", "ascending"])
    sets = {
        "descending": role == "descending",
        "ascending": role == "ascending",
        "connective": role != "none",
        "brain": np.array([True, True, True, False, False, False, False, False]),
        "vnc": np.array([False, False, False, True, True, True, False, False]),
    }
    return edges, sets


def test_layers_split_edges_by_direction_and_side():
    edges, sets = toy()
    layers = layer_edges(edges, sets)
    assert layers["D_in"].tolist() == [[0, 6], [1, 6]]
    assert layers["D_out"].tolist() == [[6, 3], [6, 4], [6, 5]]
    assert layers["A_in"].tolist() == [[3, 7]]
    assert layers["A_out"].tolist() == [[7, 0], [7, 2]]


def test_richness_ignores_connective_edges():
    edges, sets = toy()
    assert partner_richness(edges, sets["connective"]).tolist() == [1, 1, 0, 1, 1, 0, 0, 0]


def test_route_count_is_rich_inputs_times_rich_outputs():
    edges, sets = toy()
    layers = layer_edges(edges, sets)
    rich_brain = np.array([True, True, False, False, False, False, False, False])
    rich_vnc = np.array([False, False, False, True, True, False, False, False])
    # Descending: 2 rich brain inputs x 2 rich nerve-cord outputs. Ascending: 1 rich input (v0) x 1 rich output (b0).
    assert route_counts(layers, rich_brain, rich_vnc) == {"descending": 4, "ascending": 1, "total": 5}
    # Partner endpoints: D_in 2/2 rich, D_out 2/3, A_in 1/1, A_out 1/2 -> 6 of 8.
    assert rich_edge_fraction(layers, rich_brain, rich_vnc) == pytest.approx(6 / 8)


def test_rich_mask_takes_the_top_quantile_within_members():
    richness = np.array([1, 5, 9, 10, 100, 0])
    members = np.array([True, True, True, True, False, False])
    assert rich_mask(richness, members, 0.25).tolist() == [False, False, False, True, False, False]


def bipartite_layer(seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pairs = {(int(s), int(t)) for s, t in zip(rng.integers(0, 300, 3000), rng.integers(300, 340, 3000))}
    return np.array(sorted(pairs))


def test_layer_randomization_keeps_degrees_and_the_layer_direction():
    layer = bipartite_layer()
    randomized = randomize_layer(layer, 340, seed=1)
    assert len(randomized) == len(layer)
    assert np.array_equal(np.bincount(randomized[:, 0], minlength=340), np.bincount(layer[:, 0], minlength=340))
    assert np.array_equal(np.bincount(randomized[:, 1], minlength=340), np.bincount(layer[:, 1], minlength=340))
    assert (randomized[:, 0] < 300).all() and (randomized[:, 1] >= 300).all()
    assert len({tuple(e) for e in randomized.tolist()}) == len(randomized)
    assert len({tuple(e) for e in layer.tolist()} - {tuple(e) for e in randomized.tolist()}) > 0.5 * len(layer)


def test_rich_club_coefficient_matches_brute_force():
    graph = ig.Graph.Erdos_Renyi(n=60, m=500, directed=True, loops=False)
    edges = np.asarray(graph.get_edgelist())
    degree = np.asarray(graph.degree(mode="all"))
    phi, n_above = rich_club_coefficient(edges, 60)
    for k in (5, 15, 20):
        members = degree > k
        e = sum(1 for s, t in edges if members[s] and members[t])
        n = members.sum()
        assert n_above[k] == n
        assert phi[k] == pytest.approx(e / (n * (n - 1)))


def test_enrichment_null_matches_the_uniform_expectation():
    edges, sets = toy()
    layers = layer_edges(edges, sets)
    rich_brain = np.array([True, False, False, False, False, False, False, False])
    rich_vnc = np.array([False, False, False, True, False, False, False, False])
    null = enrichment_null(layers, sets, rich_brain, rich_vnc, n_nulls=20000, seed=0)
    # Each partner is rich with probability 1/3 on both sides.
    assert null.mean() == pytest.approx(1 / 3, abs=0.01)
    assert null.min() >= 0 and null.max() <= 1
