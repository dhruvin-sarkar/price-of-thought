import numpy as np
import pytest

from pipeline.length_tradeoff import (
    cut_counts,
    largest_component,
    pooled_curve,
    removal_curve,
    removal_point,
    sampled_efficiency,
    wire_at_level,
)


def chain(n: int) -> np.ndarray:
    """Edges of a directed path 0 -> 1 -> ... -> n-1."""
    return np.array([[i, i + 1] for i in range(n - 1)])


def test_a_schedule_takes_the_fewest_connections_that_reach_each_share_of_the_wire():
    lengths = np.array([1.0, 2.0, 3.0, 4.0])
    longest = np.argsort(-lengths)
    # Removing longest first takes away 4, then 7, then 9, then all 10 micrometers.
    assert cut_counts(lengths, longest, (0.0, 0.4, 0.41, 0.7, 0.9, 1.0)).tolist() == [0, 1, 2, 2, 3, 4]
    assert cut_counts(lengths, longest[::-1].copy(), (0.0, 0.1, 0.3, 1.0)).tolist() == [0, 1, 2, 4]
    # A share above one cannot ask for more connections than there are.
    assert cut_counts(lengths, longest, (2.0,)).tolist() == [4]


def test_the_largest_component_ignores_edge_direction():
    two_chains = np.concatenate([chain(4), chain(3) + 10])
    assert largest_component(13, two_chains) == 4
    assert largest_component(13, np.empty((0, 2), dtype=int)) == 1
    # A directed path is one weak component even though nothing reaches its first node.
    assert largest_component(4, chain(4)) == 4


def test_efficiency_is_the_mean_reciprocal_distance_and_counts_unreachable_pairs_as_zero():
    sources = np.arange(3)
    # On 0 -> 1 -> 2 the reachable distances are 1, 2 and 1, over six ordered pairs.
    assert sampled_efficiency(3, chain(3), sources) == pytest.approx((1 + 0.5 + 1) / 6)
    complete = np.array([[i, j] for i in range(3) for j in range(3) if i != j])
    assert sampled_efficiency(3, complete, sources) == pytest.approx(1.0)
    assert sampled_efficiency(3, np.empty((0, 2), dtype=int), sources) == 0.0


def test_a_removal_point_reports_what_it_took_and_what_it_left():
    edges = np.concatenate([chain(4), np.array([[0, 3]])])
    lengths = np.array([1.0, 1.0, 1.0, 9.0])
    longest = np.argsort(-lengths)
    point = removal_point(4, edges, lengths, longest, count=1, sources=np.arange(4))

    assert point["edges_removed"] == 1
    assert point["wire_removed_um"] == 9.0
    assert point["largest_component"] == 4
    # What is left is the path 0 -> 1 -> 2 -> 3: distances 1, 2, 3, 1, 2 and 1 over twelve ordered pairs.
    assert point["efficiency"] == pytest.approx((1 + 0.5 + 1 / 3 + 1 + 0.5 + 1) / 12, abs=5e-7)


def test_a_curve_scales_every_quantity_against_its_own_starting_point():
    edges = np.concatenate([chain(4), np.array([[0, 3]])])
    lengths = np.array([1.0, 1.0, 1.0, 9.0])
    longest = np.argsort(-lengths)
    rows = removal_curve(4, edges, lengths, longest, np.array([0, 1, 4]), np.arange(4))

    assert [r["edges_removed"] for r in rows] == [0, 1, 4]
    assert [r["edges_removed_share"] for r in rows] == [0.0, 0.25, 1.0]
    assert [r["wire_removed_um"] for r in rows] == [0.0, 9.0, 12.0]
    assert [r["wire_removed_share"] for r in rows] == [0.0, 0.75, 1.0]
    assert rows[0]["efficiency_share"] == 1.0
    assert rows[-1]["efficiency"] == 0.0
    assert [r["largest_component"] for r in rows] == [4, 4, 1]
    assert rows[1]["efficiency_share"] == pytest.approx(rows[1]["efficiency"] / rows[0]["efficiency"], abs=5e-6)


def test_pooling_repeats_reports_their_mean_and_spread_point_by_point():
    def curve(efficiency: list[float]) -> list[dict]:
        return [{"edges_removed": i, "edges_removed_share": i / 10, "wire_removed_um": 100.0 * i,
                 "wire_removed_share": i / 10, "largest_component": 10 - i, "largest_component_share": (10 - i) / 10,
                 "efficiency": e, "efficiency_share": e} for i, e in enumerate(efficiency)]

    pooled = pooled_curve([curve([1.0, 0.8, 0.6]), curve([1.0, 0.6, 0.4])])

    assert [p["edges_removed"] for p in pooled] == [0, 1, 2]
    assert [p["efficiency"] for p in pooled] == [1.0, 0.7, 0.5]
    assert pooled[0]["efficiency_sd"] == 0.0
    assert pooled[1]["efficiency_sd"] == pytest.approx(np.std([0.8, 0.6], ddof=1), abs=5e-7)
    assert pooled[2]["largest_component"] == 8.0


def test_the_crossing_is_interpolated_between_the_two_points_that_bracket_it():
    rows = [{"wire_removed_share": 0.0, "efficiency_share": 1.0},
            {"wire_removed_share": 0.2, "efficiency_share": 0.8},
            {"wire_removed_share": 0.4, "efficiency_share": 0.4}]
    # Half way between 0.8 and 0.4 in efficiency is three quarters of the way from 0.2 to 0.4 in wire.
    assert wire_at_level(rows, 0.5) == pytest.approx(0.35)
    assert wire_at_level(rows, 0.8) == pytest.approx(0.2)
    assert wire_at_level(rows, 1.0) == pytest.approx(0.0)
    assert wire_at_level(rows, 0.3) is None
    assert wire_at_level([{"wire_removed_share": 0.0, "efficiency_share": 1.0}], 0.5) is None
