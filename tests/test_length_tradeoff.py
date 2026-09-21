import igraph as ig
import numpy as np
import pytest

import pipeline.length_tradeoff as length_tradeoff
from pipeline.length_tradeoff import (
    LONGEST,
    RANDOM,
    SHORTEST,
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


def ladder_graph(n: int = 40) -> ig.Graph:
    """Types 10 µm apart on a line, each joined to the next and every second one to the type 20 along."""
    graph = ig.Graph(n=n, edges=[(i, i + 1) for i in range(n - 1)] + [(i, i + 20) for i in range(n // 2)],
                     directed=True)
    graph.vs["x"] = [float(10 * i) for i in range(n)]
    graph.vs["y"] = [0.0] * n
    graph.vs["z"] = [0.0] * n
    return graph


@pytest.fixture
def curves(monkeypatch) -> dict:
    """``tradeoff`` over the ladder graph, sampled at six shares of the wire instead of eighteen."""
    monkeypatch.setattr(length_tradeoff, "WIRE_FRACTIONS", (0.0, 0.1, 0.25, 0.5, 0.9, 1.0))
    monkeypatch.setattr(length_tradeoff, "N_SOURCES", 20)
    monkeypatch.setattr(length_tradeoff, "N_RANDOM", 3)
    return length_tradeoff.tradeoff(ladder_graph())


def test_the_three_schedules_are_sampled_over_the_same_graph(curves):
    graph, sampling = curves["graph"], curves["sampling"]

    assert graph == {"nodes": 40, "edges": 59, "total_wire_um": 4390.0,
                     "mean_length_um": pytest.approx(4390 / 59, abs=5e-3), "median_length_um": 10.0}
    assert sampling["points"] == 6
    assert (sampling["sources"], sampling["random_repeats"]) == (20, 3)
    assert set(curves["curves"]) == {LONGEST, RANDOM, SHORTEST}
    assert curves["baseline"] == {k: curves["curves"][LONGEST][0][k] for k in curves["baseline"]}
    assert all(len(rows) == 6 for rows in curves["curves"].values())


def test_taking_the_shortest_first_costs_more_connections_for_the_same_wire(curves):
    longest, shortest = curves["curves"][LONGEST], curves["curves"][SHORTEST]

    for target, long_row, short_row in zip((0.0, 0.1, 0.25, 0.5, 0.9, 1.0), longest, shortest):
        assert long_row["wire_removed_share"] >= target - 1e-9
        assert short_row["wire_removed_share"] >= target - 1e-9
        assert short_row["edges_removed"] >= long_row["edges_removed"]
    # The twenty chords hold most of the wire, so the long end reaches a quarter of it in six connections.
    assert [r["edges_removed"] for r in longest] == [0, 3, 6, 11, 20, 59]
    assert [r["wire_removed_um"] for r in longest] == [0.0, 600.0, 1200.0, 2200.0, 4000.0, 4390.0]


def test_the_random_schedule_is_matched_on_the_count_and_pooled_over_its_repeats(curves):
    longest, random = curves["curves"][LONGEST], curves["curves"][RANDOM]

    for long_row, random_row in zip(longest, random):
        assert random_row["edges_removed"] == long_row["edges_removed"]
        # Matched on the count, a random draw cannot carry away more wire than taking the longest does.
        assert random_row["wire_removed_um"] <= long_row["wire_removed_um"] + 1e-9
        assert random_row["efficiency_share_sd"] >= 0
        assert random_row["largest_component_share_sd"] >= 0
    # The draws differ from one another away from the two ends, where every schedule agrees.
    assert random[0]["efficiency_share_sd"] == 0.0
    assert any(row["wire_removed_um_sd"] > 0 for row in random[1:-1])


def test_the_reference_point_and_the_cost_per_metre_come_off_the_curves(curves):
    comparison, schedules = curves["comparison"], curves["curves"]
    reference = curves["sampling"]["wire_fractions"].index(comparison["reference_wire_fraction"])

    for name, row in comparison["at_reference"].items():
        assert row == schedules[name][reference]
        assert comparison["efficiency_lost_per_metre"][name] == pytest.approx(
            (1 - row["efficiency_share"]) / (row["wire_removed_um"] / 1e6), abs=5e-4)
    # Taking the shortest connections first buys far less connectivity per metre than taking the longest.
    assert comparison["efficiency_lost_per_metre"][SHORTEST] > comparison["efficiency_lost_per_metre"][LONGEST]


def test_the_halving_point_is_interpolated_for_every_schedule_that_reaches_it(curves):
    comparison, schedules = curves["comparison"], curves["curves"]
    half = comparison["wire_share_to_halve_efficiency"]

    for name, share in half.items():
        reached = min(row["efficiency_share"] for row in schedules[name])
        assert (share is not None) == (reached <= length_tradeoff.HALF), name
    assert comparison["halving_wire_ratio"] == pytest.approx(half[LONGEST] / half[SHORTEST], abs=5e-4)
    # Half the connectivity goes far sooner when the short connections are the ones taken away.
    assert half[SHORTEST] < half[LONGEST]


def test_no_halving_ratio_is_recorded_when_one_schedule_never_halves(monkeypatch):
    monkeypatch.setattr(length_tradeoff, "WIRE_FRACTIONS", (0.0, 0.1, 0.25, 0.5, 0.9))
    monkeypatch.setattr(length_tradeoff, "N_SOURCES", 20)
    monkeypatch.setattr(length_tradeoff, "N_RANDOM", 3)
    comparison = length_tradeoff.tradeoff(ladder_graph())["comparison"]

    assert comparison["wire_share_to_halve_efficiency"][LONGEST] is None
    assert comparison["wire_share_to_halve_efficiency"][SHORTEST] is not None
    assert "halving_wire_ratio" not in comparison
