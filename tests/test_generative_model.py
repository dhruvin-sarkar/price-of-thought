import igraph as ig
import numpy as np
import pytest

from pipeline.generative_model import (
    fit,
    logit_histogram,
    node_features,
    pair_design,
    sample_non_edges,
    solve_shift,
    write_logits,
)


def toy_graph() -> ig.Graph:
    rng = np.random.default_rng(0)
    graph = ig.Graph.Erdos_Renyi(n=40, m=300, directed=True, loops=False)
    for axis in "xyz":
        graph.vs[axis] = rng.uniform(0, 500, 40).tolist()
    graph.vs["compartment"] = ["brain"] * 25 + ["vnc"] * 15
    graph.vs["superclass"] = ["cb_intrinsic", "descending_neuron"] * 20
    return graph


def test_pair_design_columns():
    graph = toy_graph()
    nodes = node_features(graph)
    sources, targets = np.array([0, 3, 30]), np.array([1, 30, 31])
    x = pair_design(sources, targets, nodes, ("distance", "compartment", "class_pair", "degree")).toarray()
    assert x.shape == (3, 2 + 1 + 4 + 2)
    d = np.linalg.norm(nodes["positions"][0] - nodes["positions"][1])
    assert x[0, 0] == pytest.approx(d / 100) and x[0, 1] == pytest.approx(np.log(d + 1))
    assert x[:, 2].tolist() == [1.0, 0.0, 1.0]
    # Superclass codes: cb_intrinsic 0 (even nodes), descending_neuron 1 (odd); pair code = 2 * source + target.
    assert x[0, 3:7].tolist() == [0, 1, 0, 0]
    assert x[1, 3:7].tolist() == [0, 0, 1, 0]
    assert x[2, 3:7].tolist() == [0, 1, 0, 0]
    assert x[0, 7] == pytest.approx(np.log1p(graph.outdegree(0)))
    assert x[0, 8] == pytest.approx(np.log1p(graph.indegree(1)))


def test_non_edges_are_distinct_off_diagonal_and_not_edges():
    graph = toy_graph()
    edges = np.asarray(graph.get_edgelist())
    pairs = sample_non_edges(edges, 40, 800, np.random.default_rng(1))
    keys = pairs[:, 0] * 40 + pairs[:, 1]
    assert len(pairs) == 800 and len(np.unique(keys)) == 800
    assert (pairs[:, 0] != pairs[:, 1]).all()
    assert not np.isin(keys, edges[:, 0] * 40 + edges[:, 1]).any()


def test_shift_matches_the_expected_edge_count():
    centres = np.linspace(-10, 2, 601)
    counts = np.full(601, 1000.0)
    shift = solve_shift(centres, counts, 50_000)
    assert np.dot(counts, 1 / (1 + np.exp(-(centres + shift)))) == pytest.approx(50_000, rel=1e-6)


def test_logit_matrix_matches_model_predictions(tmp_path):
    graph = toy_graph()
    nodes = node_features(graph)
    terms = ("distance", "compartment", "class_pair")
    edges = np.asarray(graph.get_edgelist())
    negatives = sample_non_edges(edges, 40, 600, np.random.default_rng(2))
    pairs = np.vstack([edges, negatives])
    y = np.r_[np.ones(len(edges)), np.zeros(len(negatives))]
    model = fit(pair_design(pairs[:, 0], pairs[:, 1], nodes, terms), y)
    logits = write_logits(model, nodes, terms, -0.5, 40, tmp_path / "logits.npy")
    probe = np.array([[0, 5], [12, 33], [39, 0]])
    direct = model.decision_function(pair_design(probe[:, 0], probe[:, 1], nodes, terms)) - 0.5
    assert logits[probe[:, 0], probe[:, 1]] == pytest.approx(direct, abs=1e-4)
    assert np.isneginf(np.diag(logits)).all()
    centres, counts = logit_histogram(logits)
    assert counts.sum() == 40 * 39
