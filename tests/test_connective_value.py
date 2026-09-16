import numpy as np
import pytest

from pipeline.connective_value import (
    cost_matched_sample,
    count_matched_sample,
    graph_without,
    incident_mask,
    longest_matched,
    neck_crossing_mask,
    take_until_cost,
)
from pipeline.connectivity_metrics import flow_capacity


def test_take_until_cost_stops_at_the_closest_total_without_skipping():
    lengths = np.array([4.0, 3.0, 5.0, 10.0])
    order = np.array([0, 1, 2, 3])
    # Running totals 4, 7, 12, 22. Target 10: 7 is 3 away, 12 is 2 away, so three edges.
    assert take_until_cost(order, lengths, 10.0).tolist() == [0, 1, 2]
    # Target 8.4: 7 is 1.4 away, 12 is 3.6 away, so two edges.
    assert take_until_cost(order, lengths, 8.4).tolist() == [0, 1]
    assert take_until_cost(order, lengths, 100.0).tolist() == [0, 1, 2, 3]
    assert take_until_cost(order, lengths, 1.0).tolist() == []


def test_cost_matched_samples_hit_the_target_closely_and_vary_with_the_seed():
    rng = np.random.default_rng(0)
    lengths = rng.uniform(50, 300, size=20000)
    candidates = np.arange(20000)
    target = 400_000.0
    a = cost_matched_sample(candidates, lengths, target, np.random.default_rng(1))
    b = cost_matched_sample(candidates, lengths, target, np.random.default_rng(2))
    for sample in (a, b):
        assert abs(lengths[sample].sum() - target) <= 300
        assert len(set(sample.tolist())) == len(sample)
    assert set(a.tolist()) != set(b.tolist())


def test_samples_only_draw_from_candidates():
    lengths = np.ones(100)
    candidates = np.arange(50, 100)
    assert set(cost_matched_sample(candidates, lengths, 20, np.random.default_rng(0)).tolist()) <= set(candidates)
    count = count_matched_sample(candidates, 30, np.random.default_rng(0))
    assert len(count) == 30 and set(count.tolist()) <= set(candidates)


def test_longest_matched_takes_edges_in_decreasing_length():
    lengths = np.array([1.0, 9.0, 3.0, 7.0, 5.0])
    assert longest_matched(np.arange(5), lengths, 16.0).tolist() == [1, 3]


def test_neck_crossing_and_incident_masks():
    # 0 brain partner, 1 nerve-cord partner, 2 descending, 3 ascending.
    sets = {
        "descending": np.array([False, False, True, False]),
        "ascending": np.array([False, False, False, True]),
        "brain": np.array([True, False, False, False]),
        "vnc": np.array([False, True, False, False]),
    }
    edges = np.array([[0, 2], [2, 1], [1, 2], [1, 3], [3, 0], [0, 3], [0, 1], [2, 3]])
    assert neck_crossing_mask(edges, sets).tolist() == [False, True, True, False, True, True, False, False]
    assert incident_mask(edges, sets["descending"] | sets["ascending"]).tolist() == [
        True, True, True, True, True, True, False, True]


def test_graph_without_removes_edges_and_keeps_names():
    edges = np.array([[0, 1], [1, 2], [0, 2]])
    names = ["s", "i", "m"]
    intact = graph_without(edges, names, np.array([], dtype=int))
    assert flow_capacity(intact, ["s"], ["m"]) == 2
    cut = graph_without(edges, names, np.array([2]))
    assert cut.ecount() == 2 and cut.vs["name"] == names
    assert flow_capacity(cut, ["s"], ["m"]) == pytest.approx(1)
