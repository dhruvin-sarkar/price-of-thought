import igraph as ig
import numpy as np
import pytest

from pipeline.synapse_value import (
    DECILES,
    correlate,
    decile_index,
    decile_table,
    group_summary,
    report,
    synapse_value,
    verdict,
)


def spatial_graph(positions: np.ndarray, edges: list[tuple[int, int]], weights: list[int],
                  connective: list[str], compartments: list[str]) -> ig.Graph:
    """Directed graph carrying the positions, synapse weights and connective roles the analysis reads."""
    graph = ig.Graph(n=len(positions), edges=edges, directed=True)
    for i, axis in enumerate("xyz"):
        graph.vs[axis] = positions[:, i].tolist()
    graph.vs["connective"] = connective
    graph.vs["compartment"] = compartments
    graph.es["weight"] = weights
    return graph


def test_decile_index_puts_an_equal_count_in_each_bin():
    index = decile_index(np.arange(1.0, 101.0))
    assert np.bincount(index).tolist() == [10] * DECILES
    assert index[0] == 0
    assert index[-1] == DECILES - 1


def test_a_flat_synapse_count_makes_every_decile_buy_at_the_going_rate():
    # Ten connections of 1 µm and ten of 10 µm, each carrying five synapses.
    lengths = np.concatenate([np.ones(10), np.full(10, 10.0)])
    synapses = np.full(20, 5.0)
    rows = decile_table(lengths, synapses, deciles=2)

    assert [r["edges"] for r in rows] == [10, 10]
    assert [r["synapses"] for r in rows] == [50, 50]
    assert [r["synapses_per_um"] for r in rows] == pytest.approx([5.0, 0.5])
    assert [r["expected_per_um"] for r in rows] == pytest.approx([5.0, 0.5])
    assert [r["observed_over_expected"] for r in rows] == pytest.approx([1.0, 1.0])
    assert [r["median_synapses"] for r in rows] == [5.0, 5.0]


def test_a_decile_that_carries_more_than_its_share_sits_above_the_going_rate():
    # The long connections carry twice the synapses of the short ones, on ten times the wire.
    lengths = np.concatenate([np.ones(10), np.full(10, 10.0)])
    synapses = np.concatenate([np.full(10, 5.0), np.full(10, 10.0)])
    rows = decile_table(lengths, synapses, deciles=2)

    assert [r["synapses_per_um"] for r in rows] == pytest.approx([5.0, 1.0])
    # The going rate is the mean of 7.5 synapses over the decile's own mean length.
    assert [r["expected_per_um"] for r in rows] == pytest.approx([7.5, 0.75])
    assert [r["observed_over_expected"] for r in rows] == pytest.approx([2 / 3, 4 / 3], abs=5e-4)


def test_decile_bounds_run_from_the_shortest_connection_to_the_longest():
    lengths = np.arange(1.0, 21.0)
    rows = decile_table(lengths, np.ones(20), deciles=2)
    assert (rows[0]["min_length_um"], rows[0]["max_length_um"]) == (1.0, 10.0)
    assert (rows[1]["min_length_um"], rows[1]["max_length_um"]) == (11.0, 20.0)
    assert [r["mean_length_um"] for r in rows] == pytest.approx([5.5, 15.5])


def test_correlate_recovers_a_perfect_monotone_relationship():
    lengths = np.arange(1.0, 31.0)
    rising = correlate(lengths, lengths * 3)
    assert rising["spearman_rho"] == pytest.approx(1.0)
    assert rising["pearson_log_r"] == pytest.approx(1.0, abs=1e-6)
    assert correlate(lengths, 1000.0 / lengths)["spearman_rho"] == pytest.approx(-1.0)
    # Thirty points on an exact line leave no room for chance.
    assert rising["spearman_p"] == 0.0
    assert rising["pearson_log_p"] == 0.0


def test_correlate_reports_a_large_p_value_for_an_unrelated_pair():
    lengths = np.arange(1.0, 31.0)
    synapses = np.array([5.0, 4.0] * 15)
    unrelated = correlate(lengths, synapses)

    assert abs(unrelated["spearman_rho"]) < 0.2
    assert unrelated["spearman_p"] > 0.2
    assert unrelated["pearson_log_p"] > 0.2


PATTERN = np.array([4.0, 5.0, 6.0, 5.0, 5.0, 5.0, 4.0, 6.0, 5.0, 5.0])


def test_group_summary_totals_agree_with_its_deciles():
    # The same ten synapse counts on ten short connections and on ten long ones.
    lengths = np.concatenate([np.ones(10), np.full(10, 10.0)])
    group = group_summary(lengths, np.concatenate([PATTERN, PATTERN]))

    assert (group["edges"], group["synapses"]) == (20, 100)
    assert group["wire_um"] == pytest.approx(110.0)
    assert group["synapses_per_um"] == pytest.approx(100 / 110, abs=5e-5)
    assert group["mean_synapses"] == 5.0
    assert sum(r["edges"] for r in group["deciles"]) == 20
    assert sum(r["synapses"] for r in group["deciles"]) == 100
    # Length carries no information about synapse count when the two halves draw from the same counts.
    assert group["correlation"]["spearman_rho"] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize(("rho", "expected"), [
    (0.0, "about the same number of synapses as short ones"),
    (-0.02, "about the same number of synapses as short ones"),
    (-0.4, "fewer synapses than short ones"),
    (0.4, "more synapses than short ones"),
])
def test_verdict_reads_the_sign_and_the_size_of_the_correlation(rho, expected):
    assert verdict(rho) == expected


def test_neck_crossing_connections_are_split_from_the_rest():
    # Two descending types at 0 and 10 µm, two nerve-cord partners at 300 and 400, three brain types apart.
    positions = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [300.0, 0.0, 0.0], [400.0, 0.0, 0.0],
                          [0.0, 5.0, 0.0], [0.0, 15.0, 0.0], [0.0, 35.0, 0.0]])
    graph = spatial_graph(
        positions,
        [(0, 2), (0, 3), (1, 2), (1, 3), (4, 5), (5, 6), (4, 6)],
        [10, 20, 30, 40, 5, 15, 25],
        ["descending", "descending", "none", "none", "none", "none", "none"],
        ["brain", "brain", "vnc", "vnc", "brain", "brain", "brain"],
    )
    result = synapse_value(graph)
    crossing, rest = result["groups"]["across the neck"], result["groups"]["elsewhere"]

    assert result["totals"] == {"edges": 7, "wire_um": 1440.0, "synapses": 145, "deciles": DECILES}
    assert (crossing["edges"], crossing["synapses"]) == (4, 100)
    assert crossing["wire_um"] == pytest.approx(1380.0)
    assert crossing["synapses_per_um"] == pytest.approx(100 / 1380, abs=5e-5)
    assert crossing["mean_length_um"] == pytest.approx(345.0)
    assert (rest["edges"], rest["synapses"]) == (3, 45)
    assert rest["wire_um"] == pytest.approx(60.0)
    assert rest["synapses_per_um"] == pytest.approx(0.75, abs=5e-5)
    assert rest["mean_length_um"] == pytest.approx(20.0)
    assert result["groups"]["all"]["synapses_per_um"] == pytest.approx(145 / 1440, abs=5e-5)


def test_report_states_the_headline_numbers_it_was_given():
    # Ten connections around 1 µm holding 10 µm of wire, and ten around 10 µm holding 100 µm.
    short, long_ = np.linspace(0.9, 1.1, 10), np.linspace(9.0, 11.0, 10)
    whole = group_summary(np.concatenate([short, long_]), np.concatenate([PATTERN, PATTERN]))
    result = {
        "groups": {
            "all": whole,
            "across the neck": group_summary(long_, PATTERN),
            "elsewhere": group_summary(short, PATTERN),
        },
        "totals": {"edges": 20, "wire_um": 110.0, "synapses": 100, "deciles": DECILES},
    }
    text = report(result)

    assert "# What the wire buys" in text
    assert "The 20 connections of the cell-type graph hold 0.00 m of wire and 100 synapses" in text
    assert f"{whole['synapses_per_um']:.3f} synapses per micrometre overall" in text
    assert "a long connection carries about the same number of synapses as short ones" in text
    assert "| all | 20 | 110.0 | 100 |" in text
    assert "This is a null result" in text
    assert "![What the wire buys](synapse_value.png)" in text
