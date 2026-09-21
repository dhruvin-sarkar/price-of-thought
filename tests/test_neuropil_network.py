import json

import igraph as ig
import numpy as np
import pytest

import pipeline.neuropil_network as neuropil_network
from pipeline.wiring_cost import edge_array, edge_costs, positions_array
from pipeline.neuropil_network import (
    atlas_agreement,
    compare,
    correspondence,
    metrics,
    mirrored_pairs,
    network,
    pair_wire,
    ranked_pairs,
    region_graph,
    report,
    rewired_null,
    segment_of,
    shuffled_null,
    side_of,
    small_world,
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


def region_names(count: int) -> list[str]:
    """Four mirrored neuropils and one midline structure, enough for the side and segment labels to apply."""
    return ["AL(L)", "AL(R)", "LegNp(T2)(L)", "LegNp(T2)(R)", "GNG"][:count]


def spatial_graph() -> ig.Graph:
    """Eight cell types on a line, two in each of four regions, wired inside and between their regions."""
    graph = ig.Graph(n=8, edges=[(0, 1), (2, 3), (4, 5), (6, 7), (1, 2), (3, 4), (0, 4), (5, 6), (3, 6)],
                     directed=True)
    graph.vs["x"] = [0.0, 10.0, 40.0, 50.0, 100.0, 110.0, 160.0, 170.0]
    graph.vs["y"] = [0.0] * 8
    graph.vs["z"] = [0.0] * 8
    graph.vs["compartment"] = ["brain"] * 4 + ["vnc"] * 4
    graph.vs["cell_type"] = [f"T{i}" for i in range(8)]
    return graph


def committed_atlas(path, total: float, pairs: list[dict]) -> None:
    path.write_text(json.dumps({"totals": {"total_wire_um": total}, "pairs": pairs}), encoding="utf-8")


def test_small_world_compares_both_nulls_and_divides_the_two_ratios_into_sigma():
    graph = two_block_graph()
    world = small_world(graph, n_nulls=40, seed=21)
    real = metrics(graph)

    assert world["real"] == {k: round(v, 4) for k, v in real.items()}
    assert set(world["nulls"]) == {"rewired", "weights shuffled"}
    for label, comparisons in world["nulls"].items():
        for metric in ("clustering", "path_length", "weighted_clustering", "weighted_path_length"):
            c = comparisons[metric]
            assert c["real"] == pytest.approx(round(real[metric], 4)), f"{label} {metric}"
            assert c["ratio"] == pytest.approx(c["real"] / c["null_mean"], abs=5e-4), f"{label} {metric}"
            assert 0 <= c["n_at_or_above_real"] <= 40, f"{label} {metric}"
        for prefix in ("", "weighted_"):
            assert comparisons[f"{prefix}sigma"] == pytest.approx(
                comparisons[f"{prefix}clustering"]["ratio"] / comparisons[f"{prefix}path_length"]["ratio"],
                abs=5e-4), f"{label} {prefix}sigma"

    # Dealing the same wire out over the same edges cannot move a statistic that ignores wire, so the
    # unweighted small-world ratio against that null is one by construction; the weighted one is not.
    shuffled = world["nulls"]["weights shuffled"]
    assert (shuffled["clustering"]["ratio"], shuffled["path_length"]["ratio"], shuffled["sigma"]) == (1.0, 1.0, 1.0)
    assert shuffled["weighted_sigma"] != 1.0
    assert world["nulls"]["rewired"]["clustering"]["ratio"] > 1.0


def test_atlas_agreement_accepts_a_matrix_that_reproduces_the_committed_atlas(tmp_path, monkeypatch):
    names = ["a", "b", "c"]
    wire = np.array([[5.0, 30.0, 0.0], [30.0, 0.0, 7.0], [0.0, 7.0, 0.0]])
    counts = np.array([[1, 2, 0], [2, 0, 1], [0, 1, 0]])
    path = tmp_path / "wire_atlas.json"
    committed_atlas(path, 42.0, ranked_pairs(names, wire, counts, 2))
    monkeypatch.setattr(neuropil_network, "ATLAS", path)

    assert atlas_agreement(names, wire, counts, 42.0) == {
        "total_wire_um": 42.0, "atlas_total_wire_um": 42.0, "pairs_reproduced": 2}


def test_atlas_agreement_refuses_a_total_the_atlas_does_not_share(tmp_path, monkeypatch):
    names = ["a", "b"]
    wire = np.array([[0.0, 30.0], [30.0, 0.0]])
    counts = np.array([[0, 2], [2, 0]])
    path = tmp_path / "wire_atlas.json"
    committed_atlas(path, 41.0, ranked_pairs(names, wire, counts))
    monkeypatch.setattr(neuropil_network, "ATLAS", path)

    with pytest.raises(ValueError, match="42.0 um against 41.0 um in the atlas"):
        atlas_agreement(names, wire, counts, 42.0)


def test_atlas_agreement_refuses_a_pair_the_atlas_does_not_reproduce(tmp_path, monkeypatch):
    names = ["a", "b"]
    wire = np.array([[0.0, 30.0], [30.0, 0.0]])
    counts = np.array([[0, 2], [2, 0]])
    saved = ranked_pairs(names, wire, counts)
    saved[0]["wire_um"] = 31.0
    path = tmp_path / "wire_atlas.json"
    committed_atlas(path, 42.0, saved)
    monkeypatch.setattr(neuropil_network, "ATLAS", path)

    with pytest.raises(ValueError, match=r"1 of the atlas top pairs do not reproduce: \['a-b'\]"):
        atlas_agreement(names, wire, counts, 42.0)


@pytest.fixture
def region_network(tmp_path, monkeypatch) -> dict:
    """``network`` run over eight cell types in four of five regions, against a matching committed atlas."""
    graph = spatial_graph()
    where = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    names = region_names(5)
    edges = edge_array(graph)
    lengths = edge_costs(edges, positions_array(graph))
    wire, counts = pair_wire(where, edges, lengths, len(names))
    path = tmp_path / "wire_atlas.json"
    committed_atlas(path, round(float(lengths.sum()), 1), ranked_pairs(names, wire, counts, 5))

    monkeypatch.setattr(neuropil_network, "ATLAS", path)
    monkeypatch.setattr(neuropil_network, "assign", lambda positions: (where, np.zeros(len(positions)), names))
    monkeypatch.setattr(neuropil_network, "N_NULLS", 20)
    monkeypatch.setattr(neuropil_network, "N_PARTITION_SEEDS", 10)
    return network(graph)


def test_the_region_network_accounts_for_every_micrometre_of_the_graph_it_collapses(region_network):
    totals = region_network["totals"]

    assert totals["regions"] == 4
    assert totals["meshes"] == 5
    assert totals["region_edges"] == 5
    assert totals["possible_region_edges"] == 6
    assert totals["density"] == pytest.approx(5 / 6, abs=5e-5)
    assert totals["total_wire_um"] == 380.0
    assert totals["within_region_wire_um"] == 40.0
    assert totals["between_region_wire_um"] == 340.0
    assert totals["share_between_regions"] == pytest.approx(340 / 380, abs=5e-5)
    assert totals["n_nulls"] == 20
    assert region_network["atlas_agreement"] == {
        "total_wire_um": 380.0, "atlas_total_wire_um": 380.0, "pairs_reproduced": 5}


def test_each_region_carries_the_wire_of_its_pairs_and_half_the_wire_it_shares(region_network):
    rows = {r["neuropil"]: r for r in region_network["regions"]}

    assert [r["strength_um"] for r in region_network["regions"]] == [200.0, 190.0, 160.0, 130.0]
    # Half of the wire between two regions is credited to each, which is what the atlas records.
    assert [rows[n]["atlas_wire_um"] for n in region_names(4)] == [75.0, 105.0, 110.0, 90.0]
    assert sum(r["atlas_wire_um"] for r in region_network["regions"]) == 380.0
    assert [rows[n]["internal_um"] for n in region_names(4)] == [10.0, 10.0, 10.0, 10.0]
    assert [rows[n]["compartment"] for n in region_names(4)] == ["brain", "brain", "vnc", "vnc"]
    assert [rows[n]["types"] for n in region_names(4)] == [2, 2, 2, 2]
    assert [rows[n]["degree"] for n in region_names(4)] == [2, 3, 3, 2]
    assert sum(r["strength_share"] for r in region_network["regions"]) == pytest.approx(1.0, abs=5e-4)


def test_the_small_world_comparison_runs_over_the_collapsed_network(region_network):
    world = region_network["small_world"]

    assert world["real"]["clustering"] == pytest.approx((1 + 2 / 3 + 2 / 3 + 1) / 4, abs=5e-5)
    assert set(world["nulls"]) == {"rewired", "weights shuffled"}
    for comparisons in world["nulls"].values():
        assert comparisons["sigma"] == pytest.approx(
            comparisons["clustering"]["ratio"] / comparisons["path_length"]["ratio"], abs=5e-4)
    # Four regions of degree 2, 3, 3 and 2 admit one simple graph, so rewiring cannot move the topology.
    assert world["nulls"]["rewired"]["clustering"]["ratio"] == 1.0
    assert world["nulls"]["weights shuffled"]["path_length"]["ratio"] == 1.0


def test_the_partition_covers_every_region_and_is_compared_with_each_anatomical_label(region_network):
    communities, rows = region_network["communities"], region_network["regions"]

    assert sorted(n for c in communities for n in c["members"]) == sorted(region_names(4))
    assert region_network["partition"]["communities"] == len(communities)
    assert region_network["partition"]["seeds"] == 10
    for community in communities:
        assert community["brain_regions"] + community["vnc_regions"] == community["regions"]
        assert all(r["community"] == community["community"]
                   for r in rows if r["neuropil"] in community["members"])
    assert set(region_network["anatomy"]) == {"compartment", "side", "segment"}
    assert region_network["anatomy"]["compartment"]["regions"] == 4
    # Only the two nerve-cord regions name a segment, and both name the same one.
    assert region_network["anatomy"]["segment"]["regions"] == 2
    assert region_network["anatomy"]["segment"]["groups"] == 1
    assert region_network["mirrored"]["neuropils_on_both_sides"] == 2


def test_the_report_states_the_network_it_was_given(region_network):
    text = report(region_network)

    world = region_network["small_world"]["nulls"]["rewired"]
    assert "# Neuropil network" in text
    assert "a network of 4 regions joined by 5 weighted edges" in text
    assert "The recomputation reproduces the atlas total of 0.00 m and every pair it saves." in text
    assert "89.5% of the wire runs between two regions" in text
    assert "| AL(L) | brain | L |" in text
    assert "| LegNp(T2)(R) | vnc | R |" in text
    assert f"{world['weighted_clustering']['ratio']:.2f}" in text
