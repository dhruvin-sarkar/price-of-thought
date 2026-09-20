"""Precompute everything the project site shows into static JSON and one packed scene file."""

import base64
import json
import shutil

import numpy as np
import pandas as pd

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import ASSETS, RESULTS, ROOT
from pipeline.connective_richclub import TOP_FRACTION, node_sets, partner_richness, rich_mask
from pipeline.connective_value import neck_crossing_mask
from pipeline.hero_render import load_all_meshes, simplify
from pipeline.poster import hypotheses, load_results
from pipeline.readme_assets import PREREGISTRATION_COMMITS
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

OUT = ROOT / "web" / "public" / "data"
# Coarse enough that the merged shell stays under 65536 vertices and its triangles index as uint16.
MESH_CELL_NM = 9000.0
HIST_BINS = 40
STEPS = 65535


def read_json(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def histogram(values, bins: int = HIST_BINS) -> dict:
    """Bin edges and counts of a sample, rounded for a compact payload."""
    counts, edges = np.histogram(np.asarray(values, dtype=float), bins=bins)
    return {"edges": [float(f"{e:.6g}") for e in edges], "counts": counts.tolist()}


def quantize(values: np.ndarray, low, high) -> np.ndarray:
    """Values mapped onto the integer range 0 to STEPS spanned by low to high, per trailing axis."""
    low, high = np.asarray(low, dtype=float), np.asarray(high, dtype=float)
    span = np.where(high - low > 0, high - low, 1.0)
    return np.clip(np.rint((values - low) / span * STEPS), 0, STEPS).astype(np.uint16)


def merged_shell(meshes: dict, cell_nm: float = MESH_CELL_NM) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """All neuropil meshes decimated and merged into one vertex array (µm), one triangle index array, and the
    neuropil each vertex belongs to, indexed into the order the meshes are given in."""
    vertices, faces, group, offset = [], [], [], 0
    for i, (v, f) in enumerate(meshes.values()):
        v, f = simplify(v, f, cell_nm)
        vertices.append(v / 1000.0)
        faces.append(f + offset)
        group.append(np.full(len(v), i, dtype=np.uint8))
        offset += len(v)
    return np.concatenate(vertices), np.concatenate(faces), np.concatenate(group)


def scene(graph, price: pd.DataFrame) -> dict:
    """Shell mesh and neck-crossing wires as base64-packed typed arrays, with the offset and dtype of each array."""
    edges = edge_array(graph)
    positions = positions_array(graph)
    sets = node_sets(graph)
    crossing = neck_crossing_mask(edges, sets)
    wires = edges[crossing]
    lengths = edge_costs(edges, positions)[crossing]
    richness = partner_richness(edges, sets["connective"])
    rich = rich_mask(richness, sets["brain"], TOP_FRACTION) | rich_mask(richness, sets["vnc"], TOP_FRACTION)
    connective_end = np.where(sets["connective"][wires[:, 0]], wires[:, 0], wires[:, 1])
    partner_end = np.where(sets["connective"][wires[:, 0]], wires[:, 1], wires[:, 0])
    names = np.asarray(graph.vs["name"])
    row_of = {name: i for i, name in enumerate(price["node"])}
    node_index = np.array([row_of.get(names[i], -1) for i in connective_end], dtype=np.int32)
    if (node_index < 0).any():
        raise RuntimeError("a neck-crossing wire has a connective endpoint missing from the price table")

    meshes = load_all_meshes()
    shell_vertices, shell_faces, shell_group = merged_shell(meshes)
    if len(shell_vertices) > STEPS + 1:
        raise RuntimeError(f"{len(shell_vertices)} shell vertices do not index as uint16; coarsen MESH_CELL_NM")
    wire_ends = positions[wires]
    # Shell and wires are quantized against one box, so the two stay registered to each other.
    low = np.minimum(shell_vertices.min(axis=0), wire_ends.reshape(-1, 3).min(axis=0))
    high = np.maximum(shell_vertices.max(axis=0), wire_ends.reshape(-1, 3).max(axis=0))
    length_range = (float(lengths.min()), float(lengths.max()))

    arrays = {
        "shell_positions": quantize(shell_vertices, low, high).ravel(),
        "shell_indices": shell_faces.astype(np.uint16).ravel(),
        "shell_group": shell_group,
        "wire_positions": quantize(wire_ends, low, high).ravel(),
        "wire_length": quantize(lengths, *length_range),
        "wire_rich_partner": rich[partner_end].astype(np.uint8),
        "wire_node": node_index.astype(np.uint16),
    }
    header, chunks, offset = {"arrays": {}}, [], 0
    for key, array in arrays.items():
        raw = array.tobytes()
        pad = (-len(raw)) % 4
        header["arrays"][key] = {"offset": offset, "length": int(array.size), "dtype": str(array.dtype)}
        chunks.append(raw + b"\0" * pad)
        offset += len(raw) + pad
    header["bounds_um"] = {"min": low.tolist(), "max": high.tolist()}
    header["length_range_um"] = list(length_range)
    header["steps"] = STEPS
    header["wires"] = int(len(wires))
    header["shell_triangles"] = int(len(shell_faces))
    # One entry per mesh, in the order shell_group indexes, so the view can paint each neuropil by what it holds.
    atlas = {row["neuropil"]: row for row in read_json("wire_atlas.json")["neuropils"]}
    header["neuropils"] = [
        {
            "name": name,
            "compartment": atlas.get(name, {}).get("compartment", "brain"),
            "types": atlas.get(name, {}).get("types", 0),
            "wire_um": atlas.get(name, {}).get("wire_um", 0.0),
            "wire_share": atlas.get(name, {}).get("wire_share", 0.0),
            "cost_ratio": atlas.get(name, {}).get("cost_ratio"),
        }
        for name in meshes
    ]
    # Shipped as base64 inside JSON: download managers intercept binary URLs such as .bin.
    header["data"] = base64.b64encode(b"".join(chunks)).decode("ascii")
    return header


def front_view(front: dict) -> dict:
    """The front view with its coordinates rounded to a tenth of a micrometre, which the site draws at."""
    return {
        **{k: front[k] for k in ("bounds", "length_range_um", "crossing_edges", "sample")},
        "outlines": [[[round(x, 1), round(y, 1)] for x, y in outline] for outline in front["outlines"]],
        "wires": [[round(v, 1) for v in wire] for wire in front["wires"]],
    }


def site_data(price: pd.DataFrame) -> dict:
    """Every number and chart series the page text and charts use."""
    spatial = read_json("spatial_optimality.json")
    costs = pd.read_csv(RESULTS / "spatial_permutation_costs.csv")
    richclub = read_json("connective_richclub.json")
    route_nulls = pd.read_csv(RESULTS / "connective_richclub_nulls.csv")
    value = read_json("connective_value.json")
    value_nulls = pd.read_csv(RESULTS / "connective_value_nulls.csv")
    economy = read_json("wiring_economy_extensions.json")
    distance = pd.read_csv(RESULTS / "distance_dependence.csv")
    cable = read_json("cable_length.json")
    cable_points = pd.read_csv(RESULTS / "cable_length.csv")
    model = read_json("generative_model.json")
    comparison = read_json("generative_comparison.json")
    graph_summary = read_json("spatial_graph_summary.json")

    placement = {key: {**result, "null": histogram(costs[key])} for key, result in spatial["analyses"].items()}
    probability = {}
    for c in ("all", "brain-brain", "vnc-vnc", "cross"):
        kept = distance[distance[f"pairs_{c}"] >= 1000]
        probability[c] = {"distance_um": (kept["bin_start_um"] + 10).tolist(),
                          "probability": (kept[f"edges_{c}"] / kept[f"pairs_{c}"]).round(8).tolist()}
    value_families = {}
    for family, result in value["families"].items():
        rows = value_nulls[value_nulls["family"] == family]
        value_families[family] = {
            metric: {**result[metric], "null": histogram(value["intact"][metric] - rows[metric])}
            for metric in ("flow", "flow_brain_to_vnc", "flow_vnc_to_brain", "pairs")
        }
    routes = richclub["routes_top10"]
    data = {
        "graph": graph_summary,
        "preregistration_commits": list(PREREGISTRATION_COMMITS),
        "placement": placement,
        "distance": {"summary": economy["distance_dependence"], "minima": economy["probability_minima"],
                     "curves": probability},
        "swaps": economy["local_optimum"],
        "cost_share": economy["cost_share"],
        "compartment_optimality": economy["compartment_optimality"],
        "length_traffic": economy["length_traffic"],
        "richclub": {
            "routes": {k: {**v, "null": histogram(route_nulls[f"{k}_{TOP_FRACTION}"])} for k, v in routes.items()},
            "threshold_curve": richclub["threshold_curve"],
            "endpoint_enrichment": richclub["endpoint_enrichment"],
            "membership": richclub["whole_cns_membership"],
            "rich_club_curve": richclub["rich_club_curve"],
        },
        "value": {"intact": value["intact"], "real": value["real"], "sets": value["sets"],
                  "removal_sets": value["removal_sets"], "families": value_families},
        "price": {
            "tests": read_json("connective_price.json")["tests"],
            "nodes": price[["node", "cell_type", "side", "direction", "edges", "price_um", "value"]]
            .round({"price_um": 1}).to_dict(orient="records"),
        },
        "cable": {**cable, "points": cable_points[["superclass", "cable_um", "soma_to_output_um"]]
                  .round(1).to_dict(orient="records")},
        "generative": {"fit": model, "comparison": comparison},
        # The front view the title plate draws, so the hero can show the same still while the scene loads.
        "front": front_view(read_json("front_view.json")),
        "atlas": read_json("wire_atlas.json"),
        "concentration": read_json("wire_concentration.json"),
        # The same list the poster prints, so the site cannot drift from it or from the pre-registration index.
        "hypotheses": [{"label": label, "statement": statement, "supported": bool(supported)}
                       for label, statement, supported in hypotheses(load_results())],
    }
    robustness = RESULTS / "threshold_robustness.json"
    if robustness.exists():
        data["robustness"] = json.loads(robustness.read_text(encoding="utf-8"))
    return data


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # The card link previews use. The page itself draws its own still from the exported front view.
    shutil.copyfile(ASSETS / "hero.png", OUT.parent / "hero.png")
    price = pd.read_csv(RESULTS / "connective_price.csv")
    data = site_data(price)
    (OUT / "site.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    header = scene(load_spatial_graph(), price)
    (OUT / "scene.json").write_text(json.dumps(header, separators=(",", ":")), encoding="utf-8")
    print(f"site.json {(OUT / 'site.json').stat().st_size / 1e6:.2f} MB, scene.json "
          f"{(OUT / 'scene.json').stat().st_size / 1e6:.2f} MB, {header['wires']:,} wires, "
          f"{header['shell_triangles']:,} shell triangles")


if __name__ == "__main__":
    main()
