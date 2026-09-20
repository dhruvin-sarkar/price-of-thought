import igraph as ig
import numpy as np
import pytest

from pipeline.neuropil_network import (
    compare,
    correspondence,
    metrics,
    mirrored_pairs,
    pair_wire,
    ranked_pairs,
    region_graph,
    rewired_null,
    segment_of,
    shuffled_null,
    side_of,
    stable_partition,
)


def two_block_graph() -> ig.Graph:
    """Six regions in two triangles of heavy edges joined by one light edge."""
    names = [f"R{i}" for i in range(6)]
    wire = np.zeros((6, 6))
    counts = np.zeros((6, 6), dtype=np.int64)
    for a, b in [(0, 1), (0, 2), (1, 2), (3, 4), (3, 5), (4, 5)]:
        wire[a, b] = wire[b, a] = 100.0
        counts[a, b] = counts[b, a] = 10
    wire[2, 3] = wire[3, 2] = 1.0
    counts[2, 3] = counts[3, 2] = 1
    return region_graph(names, wire, counts)


def test_a_connection_gives_its_whole_length_to_the_one_pair_of_regions_it_joins():
    where = np.array([0, 0, 1, 2])
    edges = np.array([[0, 1], [0, 2], [1, 2], [2, 3]])
    lengths = np.array([3.0, 10.0, 20.0, 7.0])
    wire, counts = pair_wire(where, edges, lengths, 3)

    assert wire[0, 0] == pytest.approx(3.0)
    assert wire[0, 1] == wire[1, 0] == pytest.approx(30.0)
    assert wire[1, 2] == wire[2, 1] == pytest.approx(7.0)
    assert wire[0, 2] == 0.0
    assert counts.tolist() == [[1, 2, 0], [2, 0, 1], [0, 1, 0]]
    # The diagonal holds within-region wire once and every other micrometre appears twice.
    diagonal = np.diag(wire).sum()
    assert (wire.sum() + diagonal) / 2 == pytest.approx(lengths.sum())


def test_pairs_are_named_and_ranked_by_the_wire_between_them():
    wire = np.array([[5.0, 30.0, 0.0], [30.0, 0.0, 7.0], [0.0, 7.0, 0.0]])
    counts = np.array([[1, 2, 0], [2, 0, 1], [0, 1, 0]])
    pairs = ranked_pairs(["a", "b", "c"], wire, counts)

    assert pairs == [
        {"a": "a", "b": "b", "wire_um": 30.0, "edges": 2},
        {"a": "b", "b": "c", "wire_um": 7.0, "edges": 1},
        {"a": "a", "b": "a", "wire_um": 5.0, "edges": 1},
    ]
    assert ranked_pairs(["a", "b", "c"], wire, counts, limit=1) == pairs[:1]


def test_side_and_segment_are_read_off_the_neuropil_name():
    assert [side_of(n) for n in ("AVLP(L)", "AVLP(R)", "GNG", "LegNp(T2)(R)")] == ["L", "R", None, "R"]
    assert [segment_of(n) for n in ("LegNp(T2)(R)", "mVAC(T1)(L)", "GNG", "WTct(UTct-T2)(L)")] == \
        ["T2", "T1", None, "T2"]


def test_the_region_graph_carries_the_wire_between_regions_and_keeps_the_rest_on_its_nodes():
    graph = two_block_graph()

    assert graph.vcount() == 6
    assert graph.ecount() == 7
    assert sum(graph.es["wire"]) == pytest.approx(601.0)
    assert graph.vs["internal_um"] == [0.0] * 6
    assert sorted(graph.degree()) == [2, 2, 2, 2, 3, 3]


def test_two_triangles_joined_by_one_edge_are_fully_clustered_and_far_apart_by_wire():
    graph = two_block_graph()
    m = metrics(graph)

    # Every node's neighbours are joined except the two ends of the bridge.
    assert m["clustering"] == pytest.approx((1 + 1 + 1 / 3 + 1 / 3 + 1 + 1) / 6)
    assert m["weighted_clustering"] > m["clustering"]
    # The bridge carries a hundredth of the wire of any other edge, so crossing it costs a hundred steps.
    assert m["weighted_path_length"] > m["path_length"] * 10


def test_both_nulls_keep_every_region_s_partner_count_and_the_wire_values_themselves():
    graph = two_block_graph()
    for null in (rewired_null(graph, seed=11), shuffled_null(graph, seed=11)):
        assert sorted(null.degree()) == sorted(graph.degree())
        assert sorted(null.es["wire"]) == sorted(graph.es["wire"])
    # Shuffling leaves the topology alone; rewiring does not have to.
    assert shuffled_null(graph, seed=11).get_edgelist() == graph.get_edgelist()
    assert shuffled_null(graph, seed=11).es["wire"] == shuffled_null(graph, seed=11).es["wire"]
    assert shuffled_null(graph, seed=11).es["wire"] != shuffled_null(graph, seed=12).es["wire"]


def test_compare_reports_the_rank_of_a_real_value_in_its_null():
    null = np.arange(100, dtype=float)
    above = compare(90.0, null)
    assert above["null_mean"] == pytest.approx(49.5)
    assert above["ratio"] == pytest.approx(90 / 49.5, abs=5e-5)
    assert above["n_at_or_above_real"] == 10
    assert above["p_value"] == pytest.approx(2 * 11 / 101, abs=5e-5)
    # A value in the middle of its null is two-sided indistinguishable from it.
    assert compare(49.5, null)["p_value"] == pytest.approx(1.0)


def test_louvain_recovers_two_blocks_joined_by_a_thin_edge():
    graph = two_block_graph()
    membership, stability = stable_partition(graph, n_seeds=20, seed=5)

    assert stability == {"seeds": 20, "distinct_partitions": 1, "seeds_agreeing": 20}
    assert len(set(membership)) == 2
    assert membership[0] == membership[1] == membership[2]
    assert membership[3] == membership[4] == membership[5]
    assert membership[0] != membership[3]


def test_correspondence_is_one_for_a_matching_split_and_about_zero_for_an_unrelated_one():
    membership = [0, 0, 0, 1, 1, 1]
    matching = correspondence(membership, ["x", "x", "x", "y", "y", "y"])
    assert matching == {"regions": 6, "groups": 2, "adjusted_rand": 1.0, "nmi": 1.0}

    interleaved = correspondence(membership, ["x", "y", "x", "y", "x", "y"])
    assert interleaved["regions"] == 6
    assert interleaved["adjusted_rand"] == pytest.approx(0.0, abs=0.35)
    assert interleaved["nmi"] == pytest.approx(0.0, abs=0.1)

    # A label only two regions carry still compares; one region alone does not.
    assert correspondence(membership, ["x", None, None, "y", None, None])["regions"] == 2
    assert correspondence(membership, ["x", None, None, None, None, None]) is None


def test_mirrored_pairs_counts_the_neuropils_whose_two_sides_part_company():
    names = ["AL(L)", "AL(R)", "ICL(L)", "ICL(R)", "GNG", "LO(L)"]
    result = mirrored_pairs(names, [0, 0, 0, 1, 1, 0])

    assert result == {"neuropils_on_both_sides": 2, "split_across_communities": 1, "split": ["ICL"]}
