import igraph as ig
import numpy as np
import pytest

from pipeline.hub_placement import (
    BINS,
    PERMUTATIONS,
    binned,
    compare,
    correlate,
    degree_and_wire,
    distance_to_centroid,
    hub_placement,
    partner_distance,
    random_partner_distance,
    report,
)


def spatial_graph(positions: np.ndarray, compartments: list[str], edges: list[tuple[int, int]]) -> ig.Graph:
    """Directed graph carrying the position, compartment and identity attributes the analysis reads."""
    graph = ig.Graph(n=len(positions), edges=edges, directed=True)
    for i, axis in enumerate("xyz"):
        graph.vs[axis] = positions[:, i].tolist()
    graph.vs["compartment"] = compartments
    graph.vs["cell_type"] = [f"T{i:02d}" for i in range(len(positions))]
    graph.vs["side"] = ["L" if i % 2 else "R" for i in range(len(positions))]
    return graph


@pytest.fixture
def chain() -> ig.Graph:
    """Twelve types 10 µm apart on a line, each wired to the next two along, the first six in the brain."""
    positions = np.column_stack([np.arange(12) * 10.0, np.zeros(12), np.zeros(12)])
    edges = [(i, i + 1) for i in range(11)] + [(i, i + 2) for i in range(10)]
    return spatial_graph(positions, ["brain"] * 6 + ["vnc"] * 6, edges)


def test_degree_counts_both_ends_and_wire_sums_the_lengths_at_each():
    edges = np.array([[0, 1], [1, 2], [0, 2]])
    lengths = np.array([3.0, 4.0, 5.0])
    degree, wire = degree_and_wire(edges, lengths, 4)
    assert degree.tolist() == [2, 2, 2, 0]
    assert wire == pytest.approx([8.0, 7.0, 9.0, 0.0])


def test_distance_to_centroid_is_measured_from_the_mean_of_the_positions_given():
    positions = np.array([[-3.0, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, -4.0, 0.0]])
    assert distance_to_centroid(positions) == pytest.approx([3.0, 3.0, 4.0, 4.0])
    # Shifting every position leaves the centroid with it, so the distances do not move.
    assert distance_to_centroid(positions + 50) == pytest.approx([3.0, 3.0, 4.0, 4.0])


def test_correlate_recovers_a_perfect_monotone_relationship():
    distance = np.arange(1.0, 21.0)
    rising = correlate(np.exp(distance / 4), distance)
    assert rising["spearman_rho"] == pytest.approx(1.0)
    assert rising["pearson_log_r"] == pytest.approx(1.0, abs=1e-6)
    falling = correlate(np.exp(-distance / 4), distance)
    assert falling["spearman_rho"] == pytest.approx(-1.0)
    assert falling["pearson_log_r"] == pytest.approx(-1.0, abs=1e-6)


def test_binned_splits_into_equal_count_bins_ordered_by_the_value():
    values = np.arange(1.0, 101.0)
    rows = binned(values, 200.0 - values)
    assert len(rows) == BINS
    assert [r["bin"] for r in rows] == list(range(1, BINS + 1))
    assert [r["types"] for r in rows] == [10] * BINS
    assert [r["median_value"] for r in rows] == pytest.approx([5.5 + 10 * b for b in range(BINS)])
    assert [r["median_distance_um"] for r in rows] == pytest.approx([194.5 - 10 * b for b in range(BINS)])


def test_a_type_sitting_at_the_centroid_of_its_partners_is_at_no_distance_from_them():
    positions = np.array([[0.0, 0.0, 0.0], [-8.0, 0.0, 0.0], [8.0, 0.0, 0.0], [0.0, 30.0, 0.0]])
    edges = np.array([[0, 1], [0, 2], [3, 1]])
    degree = np.array([2, 2, 1, 1])
    distance = partner_distance(edges, positions, degree)
    assert distance[0] == pytest.approx(0.0)
    assert distance[2] == pytest.approx(8.0)
    assert distance[3] == pytest.approx(np.hypot(8.0, 30.0))


def test_partner_distance_is_undefined_for_a_type_with_no_partner():
    positions = np.array([[0.0, 0.0, 0.0], [5.0, 0.0, 0.0], [90.0, 0.0, 0.0]])
    distance = partner_distance(np.array([[0, 1]]), positions, np.array([1, 1, 0]))
    assert np.isnan(distance[2])
    assert distance[:2] == pytest.approx([5.0, 5.0])


def test_random_partners_are_drawn_from_the_other_types_only():
    # Every type but the first sits at the origin, so any draw that excluded itself has its centroid there.
    positions = np.zeros((6, 3))
    positions[0] = [10.0, 0.0, 0.0]
    rng = np.random.default_rng(11)
    for _ in range(50):
        assert random_partner_distance(positions, np.array([0]), np.array([3]), rng) == pytest.approx([10.0])


def test_random_partner_draws_are_reproducible_and_depend_on_the_seed():
    positions = np.random.default_rng(2).uniform(0, 100, size=(30, 3))
    index, degree = np.arange(5), np.array([2, 3, 4, 5, 6])
    first = random_partner_distance(positions, index, degree, np.random.default_rng(7))
    assert len(first) == 5
    assert (first > 0).all()
    np.testing.assert_array_equal(first, random_partner_distance(positions, index, degree,
                                                                np.random.default_rng(7)))
    assert not np.array_equal(first, random_partner_distance(positions, index, degree,
                                                             np.random.default_rng(8)))


def test_compare_reports_the_ranked_position_of_the_real_value_in_its_null():
    null = np.arange(10.0, 20.0)
    below = compare(12.5, null)
    assert below["real_um"] == 12.5
    assert below["null_mean_um"] == pytest.approx(14.5)
    assert below["ratio"] == pytest.approx(12.5 / 14.5, abs=5e-5)
    assert below["z_score"] == pytest.approx((12.5 - 14.5) / null.std(ddof=1), abs=0.05)
    assert below["n_at_or_below_real"] == 3
    assert below["p_value"] == pytest.approx(4 / 11, abs=5e-7)
    assert compare(100.0, null)["n_at_or_below_real"] == 10


def test_a_chain_wired_to_its_neighbours_puts_every_type_near_its_partners(chain):
    result = hub_placement(chain)
    whole = result["partners"]["scopes"]["all"]

    assert result["totals"] == {"types": 12, "isolated_types": 0, "connections": 21, "permutations": PERMUTATIONS}
    assert [r["scope"] for r in result["scopes"]] == ["all", "brain", "nerve cord"]
    # The twelve positions run 0 to 110 µm, so the centroid sits at 55 µm and the median type 30 µm from it;
    # each compartment holds six of them and its own centroid sits in the middle of those.
    assert [r["median_distance_um"] for r in result["scopes"]] == pytest.approx([30.0, 15.0, 15.0])
    assert [r["max_distance_um"] for r in result["scopes"]] == pytest.approx([55.0, 25.0, 25.0])
    assert result["scopes"][0]["centroid_um"] == [55.0, 0.0, 0.0]

    # Partners are the two types either side, so a type sits all but on top of their centroid.
    assert whole["real_um"] < 5.0 < whole["null_mean_um"]
    assert whole["n_at_or_below_real"] == 0
    assert whole["p_value"] == pytest.approx(1 / (PERMUTATIONS + 1), abs=5e-7)
    assert result["partners"]["types_tested"] == 12
    assert result["partners"]["share_nearer_than_chance"] == 1.0
    assert len(result["partners"]["extremes"]) == 12
    assert [r["z_score"] for r in result["partners"]["extremes"]] == sorted(
        r["z_score"] for r in result["partners"]["extremes"])


def test_report_states_the_headline_numbers_it_was_given(chain):
    result = hub_placement(chain)
    text = report(result)
    whole = result["partners"]["scopes"]["all"]
    degree = next(r for r in result["correlations"] if r["scope"] == "all" and r["measure"] == "degree")
    assert "# Hub placement" in text
    assert "Over all 12 cell types" in text
    assert f"every type's position is {degree['spearman_rho']:+.3f}" in text
    assert f"{whole['real_um']:.1f} µm against {whole['null_mean_um']:.1f} µm for random partners" in text
    assert "100.0% of types sit nearer their own partners" in text
    assert "| all | degree | 12 |" in text
    assert "![Hub placement](hub_placement.png)" in text
