"""Render the male CNS neuropils with every neck-crossing connection of the cell-type graph drawn through them."""

import json
import textwrap
import urllib.parse

import numpy as np
import requests
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_rgb
from PIL import Image

from pipeline.build_spatial_graph import load_spatial_graph
from pipeline.common import ASSETS, DATA, RESULTS
from pipeline.connective_richclub import node_sets
from pipeline.connective_value import neck_crossing_mask
from pipeline.figures import plt
from pipeline.fonts import register
from pipeline.wiring_cost import edge_array, edge_costs, positions_array

MESH_SOURCES = {
    "brain": "https://storage.googleapis.com/flyem-male-cns/rois/fullbrain-roi-v5",
    "vnc": "https://storage.googleapis.com/flyem-male-cns/rois/malecns-vnc-neuropil-roi-v0",
}
MESH_CACHE = DATA / "neuropil_meshes"
HERO_SIZE = (1920, 1080)
SUPERSAMPLE = 2
CLUSTER_NM = 2000.0
PAPER = "#f4f5f3"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
NEUROPIL = "#e4e2dc"
RAMP = LinearSegmentedColormap.from_list("wire", ["#f3c7a4", "#eb6834", "#b23a10", "#3d1204"])
LENGTH_RANGE_UM = (200.0, 1000.0)
PITCH, YAW = 18.0, 0.0


def mesh_names(source: str) -> list[str]:
    """Neuropil names published for one mesh source."""
    info = requests.get(f"{MESH_SOURCES[source]}/segment_properties/info", timeout=60).json()["inline"]
    return list(info["properties"][0]["values"])


def load_mesh(source: str, name: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Vertices (nm) and triangles of one neuropil, cached on disk; None when no mesh is published."""
    cache = MESH_CACHE / source
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{name}.ngmesh"
    if not path.exists():
        response = requests.get(f"{MESH_SOURCES[source]}/mesh/{urllib.parse.quote(name)}.ngmesh", timeout=600)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        path.write_bytes(response.content)
    raw = path.read_bytes()
    count = int(np.frombuffer(raw[:4], np.uint32)[0])
    vertices = np.frombuffer(raw[4 : 4 + 12 * count], np.float32).reshape(-1, 3).astype(np.float64)
    faces = np.frombuffer(raw[4 + 12 * count :], np.uint32).reshape(-1, 3).astype(np.int64)
    return vertices, faces


def load_all_meshes() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Every published neuropil mesh from the brain and nerve cord sources."""
    meshes = {}
    for source in MESH_SOURCES:
        for name in mesh_names(source):
            if name not in meshes:
                mesh = load_mesh(source, name)
                if mesh is not None:
                    meshes[name] = mesh
    return meshes


def simplify(vertices: np.ndarray, faces: np.ndarray, cell: float) -> tuple[np.ndarray, np.ndarray]:
    """Collapse vertices sharing a cubic cell of side ``cell`` to their centroid and drop collapsed triangles."""
    keys = np.floor(vertices / cell).astype(np.int64)
    _, cluster, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    cluster = cluster.ravel()
    centroids = np.zeros((len(counts), 3))
    np.add.at(centroids, cluster, vertices)
    centroids /= counts[:, None]
    remapped = cluster[faces]
    collapsed = ((remapped[:, 0] == remapped[:, 1]) | (remapped[:, 1] == remapped[:, 2])
                 | (remapped[:, 0] == remapped[:, 2]))
    remapped = remapped[~collapsed]
    _, first = np.unique(np.sort(remapped, axis=1), axis=0, return_index=True)
    return centroids, remapped[np.sort(first)]


def rotation(pitch: float, yaw: float) -> np.ndarray:
    """Rotation for a pitch about the left-right axis followed by a yaw about the vertical axis."""
    p, y = np.radians(pitch), np.radians(yaw)
    about_x = np.array([[1, 0, 0], [0, np.cos(p), np.sin(p)], [0, -np.sin(p), np.cos(p)]])
    about_y = np.array([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    return about_y @ about_x


def project(points_nm: np.ndarray, center: np.ndarray, view: np.ndarray) -> np.ndarray:
    """Orthographic screen coordinates (x right, y up) of points in nanometers."""
    return ((points_nm - center) @ view.T)[..., :2] * [1, -1]


def shaded_faces(meshes: dict, center: np.ndarray, view: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Screen-space neuropil triangles with Lambert-shaded colors, sorted back to front."""
    light = np.array([-0.4, -0.5, -0.77])
    light /= np.linalg.norm(light)
    base = np.asarray(to_rgb(NEUROPIL))
    polygons, colors, depths = [], [], []
    for vertices, faces in meshes.values():
        v, f = simplify(vertices, faces, CLUSTER_NM)
        triangles = ((v - center) @ view.T)[f]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
        lambert = np.abs(normals @ light)
        polygons.append(triangles[:, :, :2] * [1, -1])
        colors.append(np.clip(base * (0.62 + 0.38 * lambert)[:, None] + 0.08 * lambert[:, None] ** 10, 0, 1))
        depths.append(triangles[:, :, 2].mean(axis=1))
    order = np.argsort(-np.concatenate(depths))
    return np.concatenate(polygons)[order], np.concatenate(colors)[order]


def render(meshes: dict, segments_nm: np.ndarray, lengths: np.ndarray, headline: dict, path) -> None:
    """Neuropils painted back to front, wires on top from shortest to longest, with a title block and length scale."""
    sans, mono = register()
    view = rotation(PITCH, YAW)
    center = np.concatenate([v for v, _ in meshes.values()]).mean(axis=0)
    polygons, colors = shaded_faces(meshes, center, view)
    order = np.argsort(lengths)
    segments = project(segments_nm[order], center, view)
    norm = Normalize(*LENGTH_RANGE_UM, clip=True)
    wire_colors = RAMP(norm(lengths[order]))
    wire_colors[:, 3] = 0.035 + 0.06 * norm(lengths[order])

    scale = SUPERSAMPLE
    width, height = (side * scale for side in HERO_SIZE)
    fig = plt.figure(figsize=(width / 100, height / 100), dpi=100, facecolor=PAPER)
    ax = fig.add_axes([0.34, 0.02, 0.64, 0.96], facecolor=PAPER)
    ax.add_collection(PolyCollection(polygons, facecolors=colors, edgecolors=colors, linewidths=0.4,
                                     antialiased=False))
    ax.add_collection(LineCollection(segments, colors=wire_colors, linewidths=0.35 * scale))
    corners = np.concatenate([polygons.reshape(-1, 2), segments.reshape(-1, 2)])
    ax.set_xlim(corners[:, 0].min(), corners[:, 0].max())
    ax.set_ylim(corners[:, 1].min(), corners[:, 1].max())
    ax.set_aspect("equal")
    ax.axis("off")

    fig.text(0.045, 0.90, "The Price of Thought", color=INK, fontsize=44 * scale, fontfamily=sans, fontweight=600,
             va="top")
    fig.text(0.045, 0.835, "Wiring economy of the complete\nDrosophila male CNS connectome",
             color=INK_SECONDARY, fontsize=17 * scale, fontfamily=sans, va="top", linespacing=1.5)
    statement = textwrap.fill(
        f"Cell types sit where their wiring is {100 * (1 - headline['cost_ratio']):.0f}% shorter than under random "
        f"placement. The {headline['crossing_edges']:,} connections across the neck are "
        f"{100 * headline['edge_share']:.1f}% of all connections and {100 * headline['cost_share']:.0f}% of the wire.",
        width=44)
    fig.text(0.045, 0.70, statement, color=INK, fontsize=15 * scale, fontfamily=mono, va="top", linespacing=1.7)
    fig.text(0.045, 0.425, "Every line joins a descending or ascending cell type\nto a partner on the far side of "
             "the neck, drawn\nstraight between their positions and colored by length.",
             color=INK_SECONDARY, fontsize=13 * scale, fontfamily=sans, va="top", linespacing=1.6)

    ticks = np.arange(LENGTH_RANGE_UM[0], LENGTH_RANGE_UM[1] + 1, 200)
    bar = fig.add_axes([0.045, 0.26, 0.20, 0.018])
    bar.imshow(np.linspace(0, 1, 256)[None, :], aspect="auto", cmap=RAMP, extent=[*LENGTH_RANGE_UM, 0, 1])
    bar.set_yticks([])
    bar.set_xticks(ticks)
    bar.set_xticklabels([f"{t:.0f}" for t in ticks], fontfamily=mono, fontsize=10.5 * scale)
    bar.set_xlim(*LENGTH_RANGE_UM)
    bar.tick_params(colors=INK_SECONDARY, length=0, pad=6)
    for spine in bar.spines.values():
        spine.set_visible(False)
    fig.text(0.045, 0.222, "connection length (µm)", color=MUTED, fontsize=11 * scale, fontfamily=sans, va="top")
    fig.text(0.045, 0.06, "Data: male CNS connectome v1.0, HHMI Janelia FlyEM and Google Research\n"
             "(Berg et al., Cell 2026), CC-BY 4.0", color=MUTED, fontsize=11 * scale, fontfamily=sans, va="top",
             linespacing=1.6)

    fig.canvas.draw()
    image = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).convert("RGB")
    plt.close(fig)
    image.resize(HERO_SIZE, Image.LANCZOS).save(path, optimize=True)


def main() -> None:
    graph = load_spatial_graph()
    edges = edge_array(graph)
    positions = positions_array(graph)
    crossing = neck_crossing_mask(edges, node_sets(graph))
    lengths = edge_costs(edges, positions)[crossing]
    segments_nm = positions[edges[crossing]] * 1000.0

    optimality = json.loads((RESULTS / "spatial_optimality.json").read_text(encoding="utf-8"))
    shares = json.loads((RESULTS / "wiring_economy_extensions.json").read_text(encoding="utf-8"))["cost_share"]["rows"]
    neck = next(row for row in shares if row["label"] == "neck-crossing")
    headline = {"cost_ratio": optimality["analyses"]["primary"]["cost_ratio"], "crossing_edges": neck["edges"],
                "edge_share": neck["edge_share"], "cost_share": neck["cost_share"]}

    meshes = load_all_meshes()
    ASSETS.mkdir(exist_ok=True)
    render(meshes, segments_nm, lengths, headline, ASSETS / "hero.png")
    print(f"Rendered {len(meshes)} neuropils and {len(lengths):,} connections at {HERO_SIZE[0]}x{HERO_SIZE[1]}")


if __name__ == "__main__":
    main()
