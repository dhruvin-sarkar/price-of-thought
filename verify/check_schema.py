"""Check the connective set, the schema report and the graph summary agree with each other."""

from pipeline.schema_discovery import ASCENDING_SUPERCLASS, DESCENDING_SUPERCLASS
from verify.common import result_json, result_text, run

# The pooled cell-type graph shared with ConnectomeLens and Fault Lines.
POOLED_TYPES = 11_751
POOLED_EDGES = 243_439


def check() -> str:
    connective = result_json("connective_set.json")
    assert connective["dataset"] == "male-cns:v1.0", f"dataset {connective['dataset']}"
    assert connective["descending_superclass"] == DESCENDING_SUPERCLASS
    assert connective["ascending_superclass"] == ASCENDING_SUPERCLASS
    descending, ascending = connective["descending"], connective["ascending"]
    for label, types in (("descending", descending), ("ascending", ascending)):
        assert len(types) == len(set(types)), f"duplicate {label} types"
        assert types == sorted(types), f"{label} types not sorted"
    assert not set(descending) & set(ascending), "a type is both descending and ascending"

    schema = result_text("schema.md")
    assert f"(`{DESCENDING_SUPERCLASS}`, brain to nerve cord): {len(descending)} types" in schema, \
        "schema.md descending count differs from connective_set.json"
    assert f"(`{ASCENDING_SUPERCLASS}`, nerve cord to brain): {len(ascending)} types" in schema, \
        "schema.md ascending count differs from connective_set.json"
    assert "voxel size [8.0, 8.0, 8.0] in `nanometers`" in schema, "schema.md lost the voxel size"

    summary = result_json("spatial_graph_summary.json")
    pooled = summary["type_graph"]
    assert (pooled["types"], pooled["edges"]) == (POOLED_TYPES, POOLED_EDGES), \
        f"pooled type graph {pooled['types']} / {pooled['edges']} is not the graph shared with the other two studies"
    report = result_text("spatial_graph.md")
    graph = summary["spatial_graph"]
    assert f"{graph['nodes']:,} nodes" in report and f"{graph['edges']:,} edges" in report, \
        "spatial_graph.md node or edge count differs from the summary"
    assert f"{summary['typed_neurons']:,} neurons with a cell type" in report, "typed neuron count differs"
    return (f"{len(descending)} descending and {len(ascending)} ascending types, disjoint; pooled graph "
            f"{POOLED_TYPES:,} / {POOLED_EDGES:,} as in the other two studies; spatial graph {graph['nodes']:,} / "
            f"{graph['edges']:,}")


if __name__ == "__main__":
    run(check)
