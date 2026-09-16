import numpy as np
import pandas as pd
import pytest

from pipeline.build_spatial_graph import (
    aggregate_edges,
    build_graph,
    classify_compartments,
    combine_edges,
    hemisphere,
    node_labels,
    node_positions,
    soma_columns,
)


def test_soma_columns_convert_voxels_and_keep_missing_somata_missing():
    table = soma_columns(pd.Series([[1000, 2000, 125_000], None]))
    assert table.iloc[0].tolist() == [8.0, 16.0, 1000.0]
    assert table.iloc[1].isna().all()


def test_hemisphere_prefers_soma_side_then_root_side():
    neurons = pd.DataFrame(
        {"somaSide": ["L", "R", "M", None, None, "L"], "rootSide": [None, None, None, "R", "unknown", "R"]}
    )
    assert hemisphere(neurons).tolist() == ["L", "R", "M", "R", "unknown", "L"]


def test_node_labels_join_type_and_hemisphere():
    neurons = pd.DataFrame({"type": ["DNa01", "DNa01"], "somaSide": ["L", "R"], "rootSide": [None, None]})
    assert node_labels(neurons).tolist() == ["DNa01|L", "DNa01|R"]


def test_edges_aggregate_per_node_and_chunks_combine_exactly():
    labels = pd.Series({1: "A|L", 2: "A|L", 3: "B|R", 4: "B|R"})
    connections = pd.DataFrame({"bodyId_pre": [1, 2, 3, 1], "bodyId_post": [3, 4, 1, 2], "weight": [5, 7, 2, 9]})
    whole = aggregate_edges(connections, labels)
    by_pair = whole.set_index(["source", "target"])
    assert by_pair.loc[("A|L", "B|R"), "weight"] == 12
    assert by_pair.loc[("A|L", "B|R"), "n_connections"] == 2
    assert by_pair.loc[("A|L", "A|L"), "weight"] == 9
    parts = [aggregate_edges(connections.iloc[:2], labels), aggregate_edges(connections.iloc[2:], labels)]
    pd.testing.assert_frame_equal(combine_edges(parts), whole)
    with pytest.raises(ValueError, match="without a node label"):
        aggregate_edges(connections.assign(bodyId_post=[3, 4, 1, 99]), labels)


def positioned_neurons() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Node "A|L": two neurons with somata 10 um apart. Node "S|R": sensory, no somata.
    # Node "M|L": one soma out of three neurons, so it falls back to synapse position.
    neurons = pd.DataFrame(
        {
            "bodyId": [1, 2, 3, 4, 5, 6, 7],
            "node": ["A|L", "A|L", "S|R", "S|R", "M|L", "M|L", "M|L"],
            "soma_x": [0.0, 10.0, np.nan, np.nan, 50.0, np.nan, np.nan],
            "soma_y": [0.0, 0.0, np.nan, np.nan, 50.0, np.nan, np.nan],
            "soma_z": [0.0, 0.0, np.nan, np.nan, 50.0, np.nan, np.nan],
        }
    )
    centroids = pd.DataFrame(
        {
            "bodyId": [1, 1, 3, 3, 4, 5, 6, 7],
            "kind": ["pre", "post", "pre", "post", "pre", "pre", "pre", "post"],
            "synapses": [10, 10, 30, 10, 20, 1, 1, 2],
            "x": [100.0, 100.0, 200.0, 400.0, 100.0, 0.0, 30.0, 0.0],
            "y": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "z": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        }
    )
    return neurons, centroids


def test_node_position_uses_soma_centroid_when_most_neurons_have_a_soma():
    positions = node_positions(*positioned_neurons()).set_index("node")
    a = positions.loc["A|L"]
    assert a["position_source"] == "soma"
    assert (a["x"], a["y"], a["z"]) == (5.0, 0.0, 0.0)
    assert a["soma_spread"] == pytest.approx(5.0)
    assert a["n_neurons"] == 2 and a["n_soma"] == 2


def test_node_position_falls_back_to_synapse_weighted_centroid():
    positions = node_positions(*positioned_neurons()).set_index("node")
    s = positions.loc["S|R"]
    assert s["position_source"] == "synapse"
    # (30*200 + 10*400 + 20*100) / 60
    assert s["x"] == pytest.approx(200.0)
    assert np.isnan(s["soma_x"])
    m = positions.loc["M|L"]
    assert m["position_source"] == "synapse"
    # (1*0 + 1*30 + 2*0) / 4
    assert m["x"] == pytest.approx(7.5)
    assert m["soma_x"] == 50.0


def test_compartment_is_the_majority_of_brain_plus_vnc_synapses():
    neurons = pd.DataFrame({"bodyId": [1, 2, 3, 4, 5], "node": ["DN|L", "DN|L", "IN|R", "TIE|L", "NECK|L"]})
    roi_counts = pd.DataFrame(
        {
            "bodyId": [1, 1, 2, 3, 4, 4, 5],
            "roi": ["CentralBrain", "VNC", "Optic(L)", "VNC", "CentralBrain", "VNC", "CV"],
            "pre": [10, 30, 5, 100, 5, 5, 50],
            "post": [40, 0, 5, 0, 0, 0, 0],
        }
    )
    table = classify_compartments(roi_counts, neurons).set_index("node")
    # DN|L: brain 50 + 10, VNC 30.
    assert table.loc["DN|L", "compartment"] == "brain"
    assert table.loc["DN|L", "brain_share"] == pytest.approx(60 / 90)
    assert table.loc["IN|R", "compartment"] == "vnc"
    assert pd.isna(table.loc["TIE|L", "compartment"])
    assert pd.isna(table.loc["NECK|L", "compartment"])
    assert np.isnan(table.loc["NECK|L", "brain_share"])


def test_graph_drops_self_loops_and_weak_inputs_and_carries_node_attributes():
    nodes = pd.DataFrame({"node": ["A|L", "B|L", "C|R"], "x": [0.0, 1.0, 2.0]})
    edges = pd.DataFrame(
        {"source": ["A|L", "C|R", "A|L", "B|L"], "target": ["B|L", "B|L", "A|L", "C|R"], "weight": [99, 1, 50, 10],
         "n_connections": [1, 1, 1, 1]}
    )
    graph = build_graph(nodes, edges, min_input_fraction=0.05)
    pairs = {(graph.vs[e.source]["name"], graph.vs[e.target]["name"]) for e in graph.es}
    assert pairs == {("A|L", "B|L"), ("B|L", "C|R")}
    assert graph.vs.find("C|R")["x"] == 2.0
    with pytest.raises(ValueError, match="not in the node table"):
        build_graph(nodes.iloc[:2], edges)
