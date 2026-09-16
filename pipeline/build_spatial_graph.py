"""Fetch neurons, soma and synapse positions, and connectivity; build the spatially embedded cell-type graph."""

import json
import time
from concurrent.futures import ThreadPoolExecutor

import igraph as ig
import numpy as np
import pandas as pd
import requests
from neuprint import NeuronCriteria as NC, NotNull, fetch_adjacencies, fetch_custom, fetch_neurons

from pipeline.common import DATA, DATASET, RESULTS, get_client
from pipeline.schema_discovery import (
    COMPARTMENT_ROIS,
    NECK_ROI,
    assign_type_superclass,
    load_connective_sets,
    voxels_to_micrometers,
)

CHUNK = 10_000
CENTROID_CHUNK = 500
CENTROID_THREADS = 4
NEURON_COLUMNS = ["bodyId", "type", "instance", "superclass", "class", "subclass", "somaSide", "rootSide", "pre", "post"]
BRAIN_ROIS = COMPARTMENT_ROIS["brain"]
VNC_ROIS = COMPARTMENT_ROIS["vnc"]
# A connection enters the graph only if it supplies at least this fraction of the postsynaptic node's input
# synapses (from all typed neurons, within-node synapses included).
MIN_INPUT_FRACTION = 0.01
# A node is placed at its soma centroid when at least this share of its neurons has a soma position.
MIN_SOMA_SHARE = 0.5

NEURONS_PATH = DATA / "neurons.parquet"
NEURON_ROI_PATH = DATA / "neuron_roi_counts.parquet"
CENTROIDS_PATH = DATA / "synapse_centroids.parquet"
NODES_PATH = DATA / "spatial_nodes.parquet"
EDGES_PATH = DATA / "spatial_edges.parquet"
TYPE_EDGES_PATH = DATA / "type_edges.parquet"

CENTROID_QUERY = """\
MATCH (n:Neuron) WHERE n.bodyId IN {body_ids}
MATCH (n)-[:Contains]->(:SynapseSet)-[:Contains]->(s:Synapse)
RETURN n.bodyId AS bodyId, s.type AS kind, count(s) AS synapses,
       avg(s.location.x) AS x, avg(s.location.y) AS y, avg(s.location.z) AS z"""


def hemisphere(neurons: pd.DataFrame) -> pd.Series:
    """Hemisphere per neuron: ``somaSide`` when it is L/R/M, otherwise ``rootSide`` when L/R, else ``unknown``."""
    soma = neurons["somaSide"].where(neurons["somaSide"].isin(["L", "R", "M"]))
    root = neurons["rootSide"].where(neurons["rootSide"].isin(["L", "R"]))
    return soma.fillna(root).fillna("unknown")


def node_labels(neurons: pd.DataFrame) -> pd.Series:
    """Node label per neuron: cell type and hemisphere, ``type|side``."""
    return neurons["type"] + "|" + hemisphere(neurons)


def soma_columns(soma_location: pd.Series) -> pd.DataFrame:
    """Split ``somaLocation`` ([x, y, z] voxels or None) into ``soma_x``, ``soma_y``, ``soma_z`` in micrometers."""
    coords = np.full((len(soma_location), 3), np.nan)
    for i, value in enumerate(soma_location):
        if value is not None and not (isinstance(value, float) and np.isnan(value)):
            coords[i] = value
    um = voxels_to_micrometers(coords)
    return pd.DataFrame({"soma_x": um[:, 0], "soma_y": um[:, 1], "soma_z": um[:, 2]}, index=soma_location.index)


def aggregate_edges(connections: pd.DataFrame, body_labels: pd.Series) -> pd.DataFrame:
    """Sum neuron-to-neuron synapse counts into node-to-node edges.

    Args:
        connections: columns ``bodyId_pre``, ``bodyId_post``, ``weight``.
        body_labels: node label indexed by bodyId.

    Returns:
        Columns ``source``, ``target``, ``weight`` (summed synapses) and ``n_connections``
        (number of contributing neuron pairs).
    """
    edges = connections.assign(
        source=connections["bodyId_pre"].map(body_labels),
        target=connections["bodyId_post"].map(body_labels),
    )
    missing = edges[["source", "target"]].isna().any(axis=1)
    if missing.any():
        raise ValueError(f"{int(missing.sum())} connections reference bodies without a node label")
    return edges.groupby(["source", "target"], as_index=False, sort=True).agg(
        weight=("weight", "sum"), n_connections=("weight", "size")
    )


def combine_edges(parts: list[pd.DataFrame]) -> pd.DataFrame:
    """Merge edge tables computed on disjoint sets of source neurons."""
    return pd.concat(parts, ignore_index=True).groupby(["source", "target"], as_index=False, sort=True)[
        ["weight", "n_connections"]
    ].sum()


def node_positions(neurons: pd.DataFrame, centroids: pd.DataFrame) -> pd.DataFrame:
    """Representative position of every node, in micrometers.

    Args:
        neurons: columns ``bodyId``, ``node``, ``soma_x``, ``soma_y``, ``soma_z`` (NaN without a soma).
        centroids: per-neuron synapse centroids, columns ``bodyId``, ``kind``, ``synapses``, ``x``, ``y``, ``z``
            (micrometers).

    Returns:
        One row per node with ``n_neurons``, ``n_soma``, the soma centroid (``soma_x`` ...) and its mean
        soma-to-centroid distance ``soma_spread``, the synapse-count-weighted synapse centroid (``synapse_x`` ...),
        ``position_source`` (``soma`` when at least ``MIN_SOMA_SHARE`` of the node's neurons have a soma,
        otherwise ``synapse``) and the chosen position ``x``, ``y``, ``z``.
    """
    has_soma = neurons["soma_x"].notna()
    somata = neurons[has_soma]
    soma = somata.groupby("node")[["soma_x", "soma_y", "soma_z"]].mean()
    offsets = somata[["soma_x", "soma_y", "soma_z"]].to_numpy() - soma.loc[somata["node"]].to_numpy()
    spread = pd.Series(np.linalg.norm(offsets, axis=1), index=somata.index).groupby(somata["node"]).mean()

    syn = centroids.merge(neurons[["bodyId", "node"]], on="bodyId", how="inner")
    weighted = syn[["x", "y", "z"]].mul(syn["synapses"], axis=0).groupby(syn["node"]).sum()
    synapse = weighted.div(syn.groupby("node")["synapses"].sum(), axis=0)
    synapse.columns = ["synapse_x", "synapse_y", "synapse_z"]

    table = pd.DataFrame(
        {"n_neurons": neurons.groupby("node").size(), "n_soma": has_soma.groupby(neurons["node"]).sum()}
    )
    table = table.join(soma).join(spread.rename("soma_spread")).join(synapse)
    use_soma = (table["n_soma"] / table["n_neurons"]) >= MIN_SOMA_SHARE
    table["position_source"] = np.where(use_soma, "soma", "synapse")
    for axis in "xyz":
        table[axis] = np.where(use_soma, table[f"soma_{axis}"], table[f"synapse_{axis}"])
    return table.rename_axis("node").reset_index()


def classify_compartments(roi_counts: pd.DataFrame, neurons: pd.DataFrame) -> pd.DataFrame:
    """Brain or VNC compartment per node by majority of its synapses (pre + post) in the two compartments.

    Synapses in the neck connective and elsewhere are ignored. Nodes with no synapses in either compartment,
    or exactly half in each, get a missing compartment.
    """
    counts = roi_counts[roi_counts["roi"].isin(BRAIN_ROIS + VNC_ROIS)].merge(neurons[["bodyId", "node"]], on="bodyId")
    counts = counts.assign(
        synapses=counts["pre"] + counts["post"],
        compartment=np.where(counts["roi"].isin(BRAIN_ROIS), "brain", "vnc"),
    )
    table = counts.pivot_table(index="node", columns="compartment", values="synapses", aggfunc="sum", fill_value=0)
    table = table.reindex(columns=["brain", "vnc"], fill_value=0).reindex(sorted(neurons["node"].unique()), fill_value=0)
    total = table["brain"] + table["vnc"]
    share = table["brain"] / total.where(total > 0)
    compartment = np.select([share > 0.5, share < 0.5], ["brain", "vnc"], default=None)
    return pd.DataFrame(
        {
            "node": table.index,
            "brain_synapses": table["brain"].to_numpy(),
            "vnc_synapses": table["vnc"].to_numpy(),
            "brain_share": share.to_numpy(),
            "compartment": compartment,
        }
    ).reset_index(drop=True)


def build_graph(
    nodes: pd.DataFrame, edges: pd.DataFrame, min_input_fraction: float = MIN_INPUT_FRACTION
) -> ig.Graph:
    """Directed graph with one vertex per node-table row, named by its ``node`` column.

    Self-loops and connections below ``min_input_fraction`` of the target's input are dropped.
    Vertex attributes: ``name`` and every other node-table column. Edge attributes: ``weight``
    (synapses) and ``input_fraction``.
    """
    unknown = set(edges["source"]).union(edges["target"]) - set(nodes["node"])
    if unknown:
        raise ValueError(f"{len(unknown)} edge endpoints are not in the node table")
    synapses_in = edges.groupby("target")["weight"].sum()
    input_fraction = edges["weight"] / edges["target"].map(synapses_in)
    kept = edges.assign(input_fraction=input_fraction)
    kept = kept[(kept["source"] != kept["target"]) & (kept["input_fraction"] >= min_input_fraction)]

    graph = ig.Graph(directed=True)
    graph.add_vertices(nodes["node"].tolist())
    graph.add_edges(
        list(zip(kept["source"], kept["target"])),
        attributes={"weight": kept["weight"].tolist(), "input_fraction": kept["input_fraction"].tolist()},
    )
    for column in nodes.columns.drop("node"):
        graph.vs[column] = nodes[column].tolist()
    return graph


def load_spatial_graph(min_input_fraction: float = MIN_INPUT_FRACTION) -> ig.Graph:
    """Load the cached spatially embedded (cell type, hemisphere) graph built by :func:`main`."""
    return build_graph(pd.read_parquet(NODES_PATH), pd.read_parquet(EDGES_PATH), min_input_fraction)


def with_retries(fetch, *args, attempts: int = 5, **kwargs):
    """Call a neuPrint fetch, retrying only on dropped connections and timeouts."""
    for attempt in range(1, attempts + 1):
        try:
            return fetch(*args, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as error:
            if attempt == attempts:
                raise
            print(f"{type(error).__name__}; retry {attempt}/{attempts - 1}", flush=True)
            time.sleep(30 * attempt)


def fetch_neuron_tables(client, roi_names: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cache = DATA / "neuron_chunks"
    cache.mkdir(parents=True, exist_ok=True)
    body_ids = with_retries(
        client.fetch_custom, "MATCH (n:Neuron) WHERE n.type IS NOT NULL RETURN n.bodyId AS bodyId ORDER BY bodyId"
    )["bodyId"].tolist()
    neuron_parts, roi_parts = [], []
    for i, start in enumerate(range(0, len(body_ids), CHUNK)):
        neuron_path, roi_path = cache / f"neurons_{i:03d}.parquet", cache / f"rois_{i:03d}.parquet"
        if not (neuron_path.exists() and roi_path.exists()):
            neurons, roi_counts = with_retries(fetch_neurons, NC(bodyId=body_ids[start : start + CHUNK]))
            table = pd.concat([neurons.reindex(columns=NEURON_COLUMNS), soma_columns(neurons["somaLocation"])], axis=1)
            table.to_parquet(neuron_path, index=False)
            roi_counts.loc[roi_counts["roi"].isin(roi_names), ["bodyId", "roi", "pre", "post"]].to_parquet(
                roi_path, index=False
            )
        neuron_parts.append(pd.read_parquet(neuron_path))
        roi_parts.append(pd.read_parquet(roi_path))
        print(f"neurons: {min(start + CHUNK, len(body_ids))}/{len(body_ids)}", flush=True)
    neurons = pd.concat(neuron_parts, ignore_index=True)
    if len(neurons) != len(body_ids) or neurons["type"].isna().any():
        raise RuntimeError(f"Expected {len(body_ids)} typed neurons, fetched {len(neurons)}")
    return neurons, pd.concat(roi_parts, ignore_index=True)


def _fetch_centroid_chunk(job: tuple[int, list[int]]) -> int:
    index, body_ids = job
    path = DATA / "centroid_chunks" / f"centroids_{index:04d}.parquet"
    if not path.exists():
        rows = with_retries(fetch_custom, CENTROID_QUERY.format(body_ids=json.dumps(body_ids)))
        rows.to_parquet(path, index=False)
    return index


def fetch_synapse_centroids(body_ids: list[int]) -> pd.DataFrame:
    """Per-neuron centroid of presynaptic and of postsynaptic synapse locations, in micrometers."""
    cache = DATA / "centroid_chunks"
    cache.mkdir(parents=True, exist_ok=True)
    jobs = [(i, body_ids[s : s + CENTROID_CHUNK]) for i, s in enumerate(range(0, len(body_ids), CENTROID_CHUNK))]
    with ThreadPoolExecutor(CENTROID_THREADS) as pool:
        for done, _ in enumerate(pool.map(_fetch_centroid_chunk, jobs), start=1):
            if done % 20 == 0 or done == len(jobs):
                print(f"synapse centroids: {done}/{len(jobs)} chunks", flush=True)
    centroids = pd.concat([pd.read_parquet(cache / f"centroids_{i:04d}.parquet") for i, _ in jobs], ignore_index=True)
    centroids[["x", "y", "z"]] = voxels_to_micrometers(centroids[["x", "y", "z"]].to_numpy())
    return centroids


def fetch_edges(neurons: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(Type, hemisphere)-level and type-level edge tables, cached per chunk of source neurons."""
    cache = DATA / "adjacency_chunks"
    cache.mkdir(parents=True, exist_ok=True)
    by_body = neurons.set_index("bodyId")
    nodes, types = by_body["node"], by_body["type"]
    body_ids = by_body.index.tolist()
    node_parts, type_parts = [], []
    for i, start in enumerate(range(0, len(body_ids), CHUNK)):
        node_path, type_path = cache / f"node_{i:03d}.parquet", cache / f"type_{i:03d}.parquet"
        if not (node_path.exists() and type_path.exists()):
            _, conn = with_retries(
                fetch_adjacencies,
                NC(bodyId=body_ids[start : start + CHUNK]),
                NC(type=NotNull),
                omit_rois=True,
                weight_props=["weight"],
                batch_size=200,
                threads=4,
            )
            aggregate_edges(conn, nodes).to_parquet(node_path, index=False)
            aggregate_edges(conn, types).to_parquet(type_path, index=False)
        node_parts.append(pd.read_parquet(node_path))
        type_parts.append(pd.read_parquet(type_path))
        print(f"adjacency: {min(start + CHUNK, len(body_ids))}/{len(body_ids)}", flush=True)
    return combine_edges(node_parts), combine_edges(type_parts)


def summarize_nodes(neurons: pd.DataFrame, centroids: pd.DataFrame, roi_counts: pd.DataFrame) -> pd.DataFrame:
    """Node table: identity, majority superclass, connective role, position, and compartment."""
    connective = load_connective_sets()
    first = neurons.groupby("node").agg(cell_type=("type", "first"), side=("side", "first"))
    superclass_rows = (
        neurons.groupby(["node", "superclass"], dropna=False).size().rename("neurons").reset_index()
        .rename(columns={"node": "type"})
    )
    superclass = assign_type_superclass(superclass_rows).set_index("type")["superclass"].rename_axis("node")
    role = np.select(
        [first["cell_type"].isin(connective["descending"]), first["cell_type"].isin(connective["ascending"])],
        ["descending", "ascending"],
        default="none",
    )
    totals = neurons.groupby("node")[["pre", "post"]].sum().rename(columns={"pre": "total_pre", "post": "total_post"})
    table = first.join(superclass).assign(connective=role).join(totals).reset_index()
    table = table.merge(node_positions(neurons, centroids), on="node", validate="one_to_one")
    return table.merge(classify_compartments(roi_counts, neurons), on="node", validate="one_to_one")


def main() -> None:
    client = get_client()
    DATA.mkdir(exist_ok=True)
    if NEURONS_PATH.exists() and NEURON_ROI_PATH.exists():
        neurons = pd.read_parquet(NEURONS_PATH)
    else:
        neurons, roi_counts = fetch_neuron_tables(client, {NECK_ROI, *BRAIN_ROIS, *VNC_ROIS})
        neurons.to_parquet(NEURONS_PATH, index=False)
        roi_counts.to_parquet(NEURON_ROI_PATH, index=False)
    roi_counts = pd.read_parquet(NEURON_ROI_PATH)
    neurons = neurons.assign(side=hemisphere(neurons), node=node_labels(neurons))

    if CENTROIDS_PATH.exists():
        centroids = pd.read_parquet(CENTROIDS_PATH)
    else:
        centroids = fetch_synapse_centroids(neurons["bodyId"].tolist())
        centroids.to_parquet(CENTROIDS_PATH, index=False)

    nodes = summarize_nodes(neurons, centroids, roi_counts)
    nodes.to_parquet(NODES_PATH, index=False)
    node_edges, type_edges = fetch_edges(neurons)
    node_edges.to_parquet(EDGES_PATH, index=False)
    type_edges.to_parquet(TYPE_EDGES_PATH, index=False)

    graph = load_spatial_graph()
    type_graph = build_graph(pd.DataFrame({"node": sorted(neurons["type"].unique())}), type_edges)
    summary = {
        "dataset": DATASET,
        "typed_neurons": int(len(neurons)),
        "type_graph": {
            "types": type_graph.vcount(),
            "edges": type_graph.ecount(),
            "synapses_between_typed_neurons": int(type_edges["weight"].sum()),
        },
        "spatial_graph": {"nodes": graph.vcount(), "edges": graph.ecount()},
    }
    print(json.dumps(summary, indent=2))
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "spatial_graph_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_report(nodes, graph, summary)


def write_report(nodes: pd.DataFrame, graph: ig.Graph, summary: dict) -> None:
    """Write ``results/spatial_graph.md`` and fail if any node lacks a position or a compartment."""
    unplaced = int((~np.isfinite(nodes[["x", "y", "z"]])).any(axis=1).sum())
    unlabelled = int(nodes["compartment"].isna().sum())
    if unplaced or unlabelled:
        raise RuntimeError(f"{unplaced} nodes without a position, {unlabelled} without a compartment")
    connective = nodes[nodes["connective"] != "none"]
    table = pd.crosstab(nodes["connective"], nodes["compartment"]).reindex(["descending", "ascending", "none"])
    sources = nodes["position_source"].value_counts()
    by_synapse = nodes[nodes["position_source"] == "synapse"]
    n_sensory = int(by_synapse["superclass"].str.contains("sensory").sum())
    spread = nodes.loc[(nodes["position_source"] == "soma") & (nodes["n_soma"] > 1), "soma_spread"]
    t, s = summary["type_graph"], summary["spatial_graph"]
    lines = [
        "# Spatially embedded cell-type graph",
        "",
        f"Dataset `{DATASET}`: {summary['typed_neurons']:,} neurons with a cell type.",
        "",
        "## Nodes",
        "",
        "Each node is a cell type on one side of the body, `type|side`. The side is the soma hemisphere (`somaSide`), "
        "or for neurons without a CNS soma the hemisphere of their nerve root (`rootSide`). Pooling both sides of a "
        "bilateral type would place its centroid on the midline, away from every one of its neurons.",
        "",
        f"- {s['nodes']:,} nodes; sides: " + ", ".join(f"{k} {int(v):,}" for k, v in nodes["side"].value_counts().items()) + ".",
        f"- Position: the centroid of the node's soma positions when at least {MIN_SOMA_SHARE:.0%} of its neurons have "
        f"one ({int(sources.get('soma', 0)):,} nodes), otherwise the synapse-count-weighted centroid of its neurons' "
        f"synapses ({int(sources.get('synapse', 0)):,} nodes, {n_sensory:,} of them sensory, whose somata lie outside "
        f"the CNS). For the {len(spread):,} soma-placed nodes with more than one soma, the mean distance of a soma "
        f"from its node centroid has median {spread.median():.1f} µm, 90th percentile {spread.quantile(0.9):.1f} µm "
        f"and 99th percentile {spread.quantile(0.99):.1f} µm.",
        "- Compartment: brain-dominant if more than half of the node's synapses (pre + post) that lie in `CentralBrain`, "
        "`Optic(L)`, `Optic(R)` or `VNC` lie in the first three, VNC-dominant if fewer than half. Synapses in the neck "
        f"connective (`{NECK_ROI}`) are not counted. Every node received a label.",
        f"- Connective: nodes whose cell type is descending or ascending (`results/connective_set.json`), "
        f"{len(connective):,} of {s['nodes']:,} nodes ({len(connective) / s['nodes']:.1%}).",
        "",
        "| connective role | brain-dominant | VNC-dominant |",
        "|---|---|---|",
        *[f"| {role} | {int(row['brain']):,} | {int(row['vnc']):,} |" for role, row in table.iterrows()],
        "",
        "## Edges",
        "",
        f"A directed edge joins two nodes when the connection supplies at least {MIN_INPUT_FRACTION:.0%} of the target "
        f"node's input synapses from typed neurons; self-connections are excluded. {s['edges']:,} edges.",
        "",
        f"The same rule applied to cell types pooled across sides gives {t['types']:,} types and {t['edges']:,} edges "
        f"from {t['synapses_between_typed_neurons']:,} synapses between typed neurons, the graph used in Fault Lines "
        "and ConnectomeLens, rebuilt here from a fresh neuPrint pull.",
        "",
        f"Mean out-degree {graph.ecount() / graph.vcount():.1f}.",
        "",
    ]
    (RESULTS / "spatial_graph.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
