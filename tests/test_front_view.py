import json

import numpy as np

from pipeline import front_view
from pipeline.common import RESULTS


def disc(center, radius, n, rng):
    angle = rng.uniform(0, 2 * np.pi, n)
    r = radius * np.sqrt(rng.uniform(0, 1, n))
    return np.column_stack([center[0] + r * np.cos(angle), center[1] + r * np.sin(angle)])


def test_silhouette_traces_one_outline_around_a_dense_disc():
    points = disc((0, 0), 100, 20000, np.random.default_rng(0))
    outlines = front_view.silhouette(points, grid=4.0)
    assert len(outlines) == 1
    radius = np.hypot(*outlines[0].T)
    assert 95 < np.median(radius) < 115


def test_silhouette_fills_interior_holes():
    points = disc((0, 0), 100, 20000, np.random.default_rng(1))
    ring = points[np.hypot(*points.T) > 60]
    assert len(front_view.silhouette(ring, grid=4.0)) == 1


def test_silhouette_orders_separate_bodies_largest_first():
    rng = np.random.default_rng(2)
    points = np.concatenate([disc((0, 0), 40, 4000, rng), disc((400, 0), 120, 30000, rng)])
    outlines = front_view.silhouette(points, grid=4.0)
    assert len(outlines) == 2
    assert outlines[0][:, 0].mean() > 300


def test_wire_sample_is_sorted_unique_and_seeded():
    a = front_view.wire_sample(40000, 3000, 7)
    assert len(a) == len(np.unique(a)) == 3000
    assert np.all(np.diff(a) > 0)
    assert a.max() < 40000
    assert np.array_equal(a, front_view.wire_sample(40000, 3000, 7))
    assert not np.array_equal(a, front_view.wire_sample(40000, 3000, 8))


def test_wire_sample_caps_at_the_population():
    assert np.array_equal(front_view.wire_sample(5, 10, 0), np.arange(5))


def result(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def test_committed_front_view_is_consistent():
    summary = result("front_view.json")
    assert summary["crossing_edges"] == result("connective_value.json")["removal_sets"]["crossing"]["edges"]
    assert summary["sample"]["n"] == len(summary["wires"]) == front_view.N_WIRES
    lengths = [w[4] for w in summary["wires"]]
    assert lengths == sorted(lengths)
    lo, hi = np.array(summary["bounds"]["min"]), np.array(summary["bounds"]["max"])
    for outline in summary["outlines"]:
        points = np.array(outline)
        assert np.all(points >= lo - 0.05) and np.all(points <= hi + 0.05)
