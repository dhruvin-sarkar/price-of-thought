"""Check the spatial graph on disk against every count the results report for it."""

import numpy as np

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.connective_richclub import node_sets
from pipeline.connective_value import neck_crossing_mask
from pipeline.wiring_cost import edge_array, edge_costs, positions_array
from verify.common import Skip, data_available, result_json, result_text, run


def check() -> str:
    if not data_available():
        raise Skip("the neuPrint data cache is not on disk; committed counts are covered by the other checks")
    graph = load_spatial_graph()
    summary = result_json("spatial_graph_summary.json")["spatial_graph"]
    assert (graph.vcount(), graph.ecount()) == (summary["nodes"], summary["edges"]), "graph size differs from summary"

    edges = edge_array(graph)
    positions = positions_array(graph)
    assert np.isfinite(positions).all(), "a node has no position"
    assert not (edges[:, 0] == edges[:, 1]).any(), "self-connection in the graph"
    assert len(np.unique(edges, axis=0)) == len(edges), "duplicate edge in the graph"

    report = result_text("spatial_graph.md")
    source = np.asarray(graph.vs["position_source"])
    soma, synapse = int((source == "soma").sum()), int((source != "soma").sum())
    assert f"({soma:,} nodes)" in report and f"({synapse:,} nodes" in report, "position source counts differ"

    sets = node_sets(graph)
    richclub = result_json("connective_richclub.json")
    assert richclub["connective_nodes"] == {"descending": int(sets["descending"].sum()),
                                            "ascending": int(sets["ascending"].sum())}, "connective node counts differ"
    assert richclub["partners"] == {"brain": int(sets["brain"].sum()), "vnc": int(sets["vnc"].sum())}, \
        "partner counts differ"

    crossing = neck_crossing_mask(edges, sets)
    lengths = edge_costs(edges, positions)
    value = result_json("connective_value.json")["removal_sets"]["crossing"]
    assert int(crossing.sum()) == value["edges"], "neck-crossing edge count differs from connective_value.json"
    assert np.isclose(lengths[crossing].sum(), value["cost_um"], rtol=1e-9), "neck-crossing cost differs"
    optimality = result_json("spatial_optimality.json")["analyses"]["primary"]
    assert np.isclose(lengths.sum(), optimality["real"], rtol=1e-9), "total wiring cost differs from the placement test"
    assert f"mean {lengths.mean():.1f} µm" in result_text("spatial_optimality.md"), "mean edge length in report differs"
    return (f"{graph.vcount():,} nodes, {graph.ecount():,} edges, no loops or duplicates; connective, partner, "
            f"crossing and cost figures match every report")


if __name__ == "__main__":
    run(check)
