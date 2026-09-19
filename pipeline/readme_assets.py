"""Draw the README plates, figures and methods diagram as SVG, in light and dark variants, from the results.

Text is set as glyph outlines in the project's typefaces, Archivo and Spline Sans Mono, so every viewer renders the
same shapes and widths. Each glyph is defined once per file and placed with ``<use>``.
"""

import argparse
import json
import math
from collections.abc import Callable, Iterable, Sequence
from functools import cache
from html import escape
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

from pipeline.common import ASSETS, RESULTS

OUT_DIR = ASSETS / "readme"
WIDTH = 1760
MARGIN = 64
FACE_SPECS = {
    "sans": ("Archivo", 400),
    "sans_medium": ("Archivo", 500),
    "sans_bold": ("Archivo", 600),
    "mono": ("Spline Sans Mono", 400),
    "mono_medium": ("Spline Sans Mono", 500),
}
# DejaVu ships with matplotlib; it stands in for a face that cannot be loaded and for glyphs a face lacks.
FALLBACK_FILES = {
    "sans": "DejaVuSans.ttf",
    "sans_medium": "DejaVuSans.ttf",
    "sans_bold": "DejaVuSans-Bold.ttf",
    "mono": "DejaVuSansMono.ttf",
    "mono_medium": "DejaVuSansMono.ttf",
}

THEMES = {
    "light": {
        "ground": "#f4f5f3",
        "border": None,
        "plate": "#fbfbfa",
        "track": "#e6e6e1",
        "rule": "#d9d8d3",
        "rule_strong": "#a9a8a2",
        "ink": "#0b0b0b",
        "ink2": "#52514e",
        "ink3": "#6a6964",
        "axis": "#85847e",
        "wire": "#d4541f",
        "wire_ink": "#8f2e0c",
        "null": "#2a78d6",
        "ramp": ("#f3c7a4", "#eb6834", "#b23a10", "#3d1204"),
    },
    "dark": {
        "ground": "#0b0b0b",
        "border": "#262724",
        "plate": "#121311",
        "track": "#1d1e1b",
        "rule": "#2a2b28",
        "rule_strong": "#57574f",
        "ink": "#eeeeea",
        "ink2": "#a8a7a0",
        "ink3": "#8f8e88",
        "axis": "#8f8e88",
        "wire": "#f07a45",
        "wire_ink": "#ff9a6b",
        "null": "#5b9cf0",
        "ramp": ("#4a1a08", "#b23a10", "#eb6834", "#f7cfae"),
    },
}
PREREGISTRATION_COMMITS = ("39892c5", "e62c6df", "73fba33")
TYPED_NEURONS = 164_506


# Formatting and geometry helpers.

def linear(d0: float, d1: float, r0: float, r1: float) -> Callable[[float], float]:
    """Map the data interval [d0, d1] onto the canvas interval [r0, r1]."""
    return lambda v: r0 + (v - d0) / (d1 - d0) * (r1 - r0)


def pct(value: float, digits: int = 1) -> str:
    """Format a fraction as a percentage, e.g. 0.0753 -> '7.5%'."""
    return f"{100 * value:.{digits}f}%"


def count(value: float) -> str:
    """Format an integer with thousands separators."""
    return f"{int(round(value)):,}"


def signed(value: float, digits: int) -> str:
    """A number with a typographic minus sign."""
    return f"{value:.{digits}f}".replace("-", "−")


def num(value: float) -> str:
    """Compact coordinate for SVG output: one decimal, trailing zeros dropped."""
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Parse '#rrggbb' into an (r, g, b) tuple."""
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def ramp_color(stops: Sequence[str], t: float) -> str:
    """Color at position ``t`` in [0, 1] along evenly spaced hex ``stops``."""
    t = min(max(t, 0.0), 1.0)
    scaled = t * (len(stops) - 1)
    i = min(int(scaled), len(stops) - 2)
    f = scaled - i
    a, b = hex_to_rgb(stops[i]), hex_to_rgb(stops[i + 1])
    return "#" + "".join(f"{round(x + (y - x) * f):02x}" for x, y in zip(a, b))


def spread(positions: Sequence[float], gap: float, lo: float = -math.inf, hi: float = math.inf) -> list[float]:
    """Move label positions apart so neighbours are at least ``gap`` apart, keeping the input order.

    Parameters: positions, the preferred coordinates; gap, the minimum separation; lo and hi, bounds.
    Returns the adjusted coordinates in the original order.
    """
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    clusters: list[list[float]] = []
    for i in order:
        clusters.append([positions[i]])
        while len(clusters) > 1:
            prev, last = clusters[-2], clusters[-1]
            if cluster_start(prev, gap) + len(prev) * gap <= cluster_start(last, gap):
                break
            clusters[-2:] = [prev + last]
    placed = [cluster_start(c, gap) + k * gap for c in clusters for k in range(len(c))]
    for k in range(len(placed)):
        placed[k] = max(placed[k], lo if k == 0 else placed[k - 1] + gap)
    for k in range(len(placed) - 1, -1, -1):
        placed[k] = min(placed[k], hi if k == len(placed) - 1 else placed[k + 1] - gap)
    result = [0.0] * len(positions)
    for rank, i in enumerate(order):
        result[i] = placed[rank]
    return result


def cluster_start(members: Sequence[float], gap: float) -> float:
    """First position of evenly spaced labels whose mean offset from ``members`` is zero."""
    return sum(m - k * gap for k, m in enumerate(members)) / len(members)


def histogram_outline(values: np.ndarray, edges: np.ndarray) -> tuple[list[float], list[float]]:
    """Step outline of a histogram in data units, tallest bin at height 1; returns (xs, heights)."""
    counts, _ = np.histogram(values, bins=edges)
    heights = counts / counts.max()
    xs, ys = [float(edges[0])], [0.0]
    for left, right, h in zip(edges[:-1], edges[1:], heights):
        xs += [float(left), float(right)]
        ys += [float(h), float(h)]
    xs.append(float(edges[-1]))
    ys.append(0.0)
    return xs, ys


# Typefaces.

class Face:
    """A static TrueType font read for glyph outlines, advance widths and pair kerning."""

    def __init__(self, path: Path) -> None:
        self.font = TTFont(path, lazy=True)
        self.key = path.stem
        self.upem = self.font["head"].unitsPerEm
        self.cmap = self.font.getBestCmap()
        self.glyphs = self.font.getGlyphSet()
        self.metrics = self.font["hmtx"].metrics
        self._pairs = pair_subtables(self.font)
        self._kerning: dict[tuple[str, str], int] = {}

    def glyph(self, ch: str) -> str | None:
        return self.cmap.get(ord(ch))

    def advance(self, glyph: str) -> int:
        return self.metrics[glyph][0]

    def kern(self, left: str, right: str) -> int:
        """Horizontal adjustment between two glyphs from the first matching GPOS pair subtable, in font units."""
        key = (left, right)
        if key not in self._kerning:
            self._kerning[key] = pair_adjustment(self._pairs, left, right)
        return self._kerning[key]

    def outline(self, glyph: str) -> str:
        """SVG path data for ``glyph`` in font units, y up."""
        pen = SVGPathPen(self.glyphs, ntos=lambda v: num(v))
        self.glyphs[glyph].draw(pen)
        return pen.getCommands()


def pair_subtables(font: TTFont) -> list[tuple[object, dict[str, int]]]:
    """Pair-positioning subtables of the 'kern' feature, each with its coverage as a glyph-to-index map."""
    if "GPOS" not in font:
        return []
    table = font["GPOS"].table
    indices = sorted({i for record in table.FeatureList.FeatureRecord if record.FeatureTag == "kern"
                      for i in record.Feature.LookupListIndex})
    found = []
    for index in indices:
        lookup = table.LookupList.Lookup[index]
        for subtable in lookup.SubTable:
            kind = subtable.ExtensionLookupType if lookup.LookupType == 9 else lookup.LookupType
            subtable = getattr(subtable, "ExtSubTable", subtable)
            if kind == 2:
                found.append((subtable, {g: i for i, g in enumerate(subtable.Coverage.glyphs)}))
    return found


def pair_adjustment(subtables: Sequence[tuple[object, dict[str, int]]], left: str, right: str) -> int:
    """X advance adjustment for the glyph pair, 0 when no subtable covers it."""
    for subtable, coverage in subtables:
        if left not in coverage:
            continue
        if subtable.Format == 1:
            for record in subtable.PairSet[coverage[left]].PairValueRecord:
                if record.SecondGlyph == right:
                    return getattr(record.Value1, "XAdvance", None) or 0
            continue
        first = subtable.ClassDef1.classDefs.get(left, 0)
        second = subtable.ClassDef2.classDefs.get(right, 0)
        return getattr(subtable.Class1Record[first].Class2Record[second].Value1, "XAdvance", None) or 0
    return 0


def project_fonts() -> dict[str, Path]:
    """Static files of the project's faces, by role, from the font cache that ``pipeline.fonts`` fills."""
    from pipeline.fonts import download_fonts

    found: dict[str, Path] = {}
    for path in download_fonts():
        font = TTFont(path, lazy=True)
        name = font["name"].getDebugName(1)
        family = "Spline Sans Mono" if name.startswith("Spline Sans Mono") else name.split(" ")[0]
        for role, spec in FACE_SPECS.items():
            if spec == (family, font["OS/2"].usWeightClass):
                found[role] = path
    return found


@cache
def faces() -> dict[str, tuple[Face, ...]]:
    """Each text role's face followed by its DejaVu fallback."""
    built = project_fonts()
    fallback_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    return {role: tuple(([Face(built[role])] if role in built else []) + [Face(fallback_dir / fallback)])
            for role, fallback in FALLBACK_FILES.items()}


def role_for(weight: int = 400, mono: bool = False) -> str:
    """Text role for a weight and family."""
    if mono:
        return "mono_medium" if weight >= 500 else "mono"
    if weight >= 600:
        return "sans_bold"
    return "sans_medium" if weight >= 500 else "sans"


def layout(s: str, size: float, role: str) -> tuple[list[tuple[Face, str, float]], float]:
    """Glyphs of ``s`` with their x offsets in canvas units, kerned within a face, and the total advance."""
    chain = faces()[role]
    placed: list[tuple[Face, str, float]] = []
    x = 0.0
    previous: tuple[Face, str] | None = None
    for ch in s:
        face, glyph = next(((f, g) for f in chain if (g := f.glyph(ch))), (chain[-1], ".notdef"))
        scale = size / face.upem
        if previous and previous[0] is face:
            x += face.kern(previous[1], glyph) * scale
        placed.append((face, glyph, x))
        x += face.advance(glyph) * scale
        previous = (face, glyph)
    return placed, x


def text_width(s: str, size: float, weight: int = 400, mono: bool = False) -> float:
    """Rendered width of ``s`` in canvas units, measured from the glyph advances and kerning."""
    return layout(s, size, role_for(weight, mono))[1]


def wrap(s: str, size: float, max_width: float, weight: int = 400) -> list[str]:
    """Greedy word wrap of ``s`` so that each line fits ``max_width``."""
    lines: list[str] = []
    current = ""
    for word in s.split():
        candidate = f"{current} {word}".strip()
        if current and text_width(candidate, size, weight) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


# SVG drawing.

class Svg:
    """An SVG canvas 1760 units wide on a rounded ground, drawn in one theme."""

    def __init__(self, height: int, theme: str, field: bool = False) -> None:
        self.height = height
        self.theme_name = theme
        self.theme = THEMES[theme]
        self.field = field
        self.parts: list[str] = []
        self.glyph_ids: dict[tuple[str, str], str] = {}
        self.glyph_defs: list[str] = []

    def c(self, name: str) -> str:
        """Resolve a theme token or a literal color."""
        value = self.theme.get(name)
        return value if isinstance(value, str) else name

    def glyph_ref(self, face: Face, glyph: str) -> str | None:
        """Id of the shared definition of ``glyph``, added on first use; None for a glyph with no outline."""
        key = (face.key, glyph)
        if key not in self.glyph_ids:
            outline = face.outline(glyph)
            self.glyph_ids[key] = f"g{len(self.glyph_defs)}" if outline else ""
            if outline:
                self.glyph_defs.append(f'<path id="{self.glyph_ids[key]}" d="{outline}"/>')
        return self.glyph_ids[key] or None

    def text(self, x: float, y: float, s: str, size: float = 26, color: str = "ink", weight: int = 400,
             anchor: str = "start", mono: bool = False) -> float:
        """Set ``s`` as outlines with its baseline at ``y``; returns the width drawn."""
        placed, width = layout(s, size, role_for(weight, mono))
        start = x - {"start": 0, "middle": width / 2, "end": width}[anchor]
        groups: list[tuple[Face, list[tuple[str, float]]]] = []
        for face, glyph, offset in placed:
            if not groups or groups[-1][0] is not face:
                groups.append((face, []))
            groups[-1][1].append((glyph, offset))
        for face, glyphs in groups:
            self.glyph_group(face, glyphs, size, start, y, self.c(color))
        return width

    def glyph_group(self, face: Face, glyphs: Sequence[tuple[str, float]], size: float, x: float, y: float,
                    fill: str) -> None:
        """One group of glyphs from a single face, scaled from font units and offset from the first glyph."""
        scale = size / face.upem
        first = glyphs[0][1]
        uses = []
        for glyph, offset in glyphs:
            ref = self.glyph_ref(face, glyph)
            if ref:
                shift = round((offset - first) / scale)
                uses.append(f'<use href="#{ref}"' + (f' x="{shift}"' if shift else "") + "/>")
        if uses:
            self.parts.append(
                f'<g transform="matrix({scale:.6g} 0 0 {-scale:.6g} {num(x + first)} {num(y)})" '
                f'fill="{fill}">{"".join(uses)}</g>'
            )

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str, width: float = 2,
             dash: str | None = None, opacity: float | None = None, cap: str | None = None) -> None:
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        extra += f' stroke-opacity="{opacity}"' if opacity is not None else ""
        extra += f' stroke-linecap="{cap}"' if cap else ""
        self.parts.append(
            f'<path d="M{num(x1)} {num(y1)}L{num(x2)} {num(y2)}" stroke="{self.c(color)}" '
            f'stroke-width="{num(width)}" fill="none"{extra}/>'
        )

    def polyline(self, xs: Iterable[float], ys: Iterable[float], color: str, width: float = 3,
                 dash: str | None = None, opacity: float | None = None) -> None:
        d = "M" + "L".join(f"{num(x)} {num(y)}" for x, y in zip(xs, ys))
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        extra += f' stroke-opacity="{opacity}"' if opacity is not None else ""
        self.parts.append(
            f'<path d="{d}" stroke="{self.c(color)}" stroke-width="{num(width)}" fill="none" '
            f'stroke-linejoin="round" stroke-linecap="round"{extra}/>'
        )

    def polygon(self, xs: Iterable[float], ys: Iterable[float], fill: str, opacity: float = 1) -> None:
        d = "M" + "L".join(f"{num(x)} {num(y)}" for x, y in zip(xs, ys)) + "Z"
        self.parts.append(f'<path d="{d}" fill="{self.c(fill)}" fill-opacity="{opacity}"/>')

    def rect(self, x: float, y: float, w: float, h: float, fill: str, rx: float = 0, stroke: str | None = None,
             stroke_width: float = 2, opacity: float | None = None) -> None:
        extra = f' rx="{num(rx)}"' if rx else ""
        extra += f' stroke="{self.c(stroke)}" stroke-width="{num(stroke_width)}"' if stroke else ""
        extra += f' fill-opacity="{opacity}"' if opacity is not None else ""
        self.parts.append(
            f'<rect x="{num(x)}" y="{num(y)}" width="{num(max(w, 0))}" height="{num(max(h, 0))}" '
            f'fill="{self.c(fill)}"{extra}/>'
        )

    def circle(self, cx: float, cy: float, r: float, fill: str, stroke: str | None = None, stroke_width: float = 3,
               opacity: float | None = None) -> None:
        extra = f' stroke="{self.c(stroke)}" stroke-width="{num(stroke_width)}"' if stroke else ""
        extra += f' fill-opacity="{opacity}"' if opacity is not None else ""
        self.parts.append(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}" fill="{self.c(fill)}"{extra}/>')

    def dot(self, cx: float, cy: float, r: float, color: str, hollow: bool = False, ring: float = 0) -> None:
        """Filled or hollow marker, with an optional ground-colored halo of width ``ring``."""
        ground = "#000000" if self.field else "ground"
        if ring:
            self.circle(cx, cy, r + ring, ground)
        if hollow:
            self.circle(cx, cy, r - 1.5, ground, stroke=color, stroke_width=3)
        else:
            self.circle(cx, cy, r, color)

    def raw(self, fragment: str) -> None:
        self.parts.append(fragment)

    def render(self, title: str, desc: str) -> str:
        """Complete SVG document with title, description, ground and every drawn part."""
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {self.height}" width="{WIDTH}" '
            f'height="{self.height}" role="img" aria-labelledby="t d">'
            f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
        )
        defs = f"<defs>{''.join(self.glyph_defs)}</defs>" if self.glyph_defs else ""
        if self.field:
            ground = f'<rect width="{WIDTH}" height="{self.height}" rx="16" fill="#000000"/>'
        elif self.theme["border"]:
            ground = (
                f'<rect x="1" y="1" width="{WIDTH - 2}" height="{self.height - 2}" rx="15" '
                f'fill="{self.theme["ground"]}" stroke="{self.theme["border"]}" stroke-width="2"/>'
            )
        else:
            ground = f'<rect width="{WIDTH}" height="{self.height}" rx="16" fill="{self.theme["ground"]}"/>'
        return head + defs + ground + "".join(self.parts) + "</svg>\n"


def heading(svg: Svg, y: float, title: str, subtitle: str | None = None, x: float = MARGIN) -> None:
    svg.text(x, y, title, 34, weight=600)
    if subtitle:
        for k, line in enumerate(wrap(subtitle, 26, WIDTH - 2 * MARGIN)):
            svg.text(x, y + 42 + k * 36, line, 26, "ink2")


def x_axis(svg: Svg, to_x: Callable, y: float, ticks: Sequence[float], labels: Sequence[str], x0: float,
           x1: float, title: str | None = None, grid_top: float | None = None) -> None:
    """Axis line with ticks and labels below ``y``, and optional vertical grid lines up to ``grid_top``."""
    for v, label in zip(ticks, labels):
        if grid_top is not None:
            svg.line(to_x(v), grid_top, to_x(v), y, "rule", 1)
        svg.line(to_x(v), y, to_x(v), y + 8, "axis", 2)
        svg.text(to_x(v), y + 36, label, 22, "ink2", anchor="middle", mono=True)
    svg.line(x0, y, x1, y, "axis", 2)
    if title:
        svg.text((x0 + x1) / 2, y + 76, title, 24, "ink2", anchor="middle")


def y_axis(svg: Svg, to_y: Callable, x: float, ticks: Sequence[float], labels: Sequence[str], y0: float,
           y1: float, grid_right: float | None = None) -> None:
    """Axis line with ticks and labels left of ``x``, and optional horizontal grid lines to ``grid_right``."""
    for v, label in zip(ticks, labels):
        if grid_right is not None:
            svg.line(x, to_y(v), grid_right, to_y(v), "rule", 1)
        svg.line(x - 8, to_y(v), x, to_y(v), "axis", 2)
        svg.text(x - 14, to_y(v) + 8, label, 22, "ink2", anchor="end", mono=True)
    svg.line(x, y0, x, y1, "axis", 2)


# Inputs.

def load_inputs(results: Path = RESULTS) -> dict:
    """Read every results file the README assets are drawn from."""
    def read(name: str) -> dict:
        return json.loads((results / name).read_text(encoding="utf-8"))

    return {
        "graph": read("spatial_graph_summary.json"),
        "placement": read("spatial_optimality.json")["analyses"],
        "economy": read("wiring_economy_extensions.json"),
        "richclub": read("connective_richclub.json"),
        "value": read("connective_value.json"),
        "value_nulls": pd.read_csv(results / "connective_value_nulls.csv"),
        "price": read("connective_price.json"),
        "price_nodes": pd.read_csv(results / "connective_price.csv"),
        "fits": read("generative_model.json"),
        "comparison": read("generative_comparison.json"),
        "robustness": read("threshold_robustness.json"),
        "distance": pd.read_csv(results / "distance_dependence.csv"),
        "front": read("front_view.json"),
    }


def headline(data: dict) -> dict:
    """Numbers shared by the plates, the figures and their descriptions."""
    shares = {row["label"]: row for row in data["economy"]["cost_share"]["rows"]}
    value = data["value"]
    families = value["families"]
    routes = {r["fraction"]: r["routes"]["total"] for r in data["robustness"]["thresholds"]}
    swaps = data["economy"]["local_optimum"]
    primary = data["placement"]["primary"]
    return {
        "nodes": data["graph"]["spatial_graph"]["nodes"],
        "edges": data["graph"]["spatial_graph"]["edges"],
        "ratio": primary["cost_ratio"],
        "within": data["placement"]["within_compartment"]["cost_ratio"],
        "swap": swaps["reduction"],
        "swap_ratio": swaps["final_cost"] / primary["null_mean"],
        "neck_edges": shares["neck-crossing"]["edges"],
        "neck_edge_share": shares["neck-crossing"]["edge_share"],
        "neck_cost_share": shares["neck-crossing"]["cost_share"],
        "neck_mean": shares["neck-crossing"]["mean_length_um"],
        "mean_length": primary["real"] / data["graph"]["spatial_graph"]["edges"],
        "odds": data["richclub"]["whole_cns_membership"]["odds_ratio"],
        "routes": data["richclub"]["routes_top10"]["total"]["ratio"],
        "routes_low": routes[0.005]["ratio"],
        "value_ratio": families["crossing_cost"]["flow"]["ratio"],
        "value_b2v": families["crossing_cost"]["flow_brain_to_vnc"]["ratio"],
        "lost": families["crossing_cost"]["flow"]["real"],
        "lost_longest": value["intact"]["flow"] - value["real"]["longest"]["flow"],
    }


# Plates.

def front_layer(svg: Svg, front: dict, x0: float, y0: float, size: float, theme: str, width: float = 1.3,
                opacity: float = 0.6) -> None:
    """Draw the CNS silhouette and the sampled neck-crossing wires, shortest first, into a square box."""
    lo, hi = np.array(front["bounds"]["min"]), np.array(front["bounds"]["max"])
    scale = size / float((hi - lo).max())
    ox = x0 + (size - (hi[0] - lo[0]) * scale) / 2
    oy = y0 + (size - (hi[1] - lo[1]) * scale) / 2

    def to_canvas(x: float, y: float) -> tuple[float, float]:
        return ox + (x - lo[0]) * scale, oy + (hi[1] - y) * scale

    for outline in front["outlines"]:
        points = [to_canvas(x, y) for x, y in outline]
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        svg.polygon(xs, ys, "track")
        svg.polyline(xs + xs[:1], ys + ys[:1], "rule_strong", 2)
    a, b = front["length_range_um"]
    stops = THEMES[theme]["ramp"]
    runs: list[tuple[str, list[str]]] = []
    for x1, y1, x2, y2, length in front["wires"]:
        color = ramp_color(stops, (length - a) / (b - a))
        (p, q), (r, s) = to_canvas(x1, y1), to_canvas(x2, y2)
        if not runs or runs[-1][0] != color:
            runs.append((color, []))
        runs[-1][1].append(f"M{num(p)} {num(q)}L{num(r)} {num(s)}")
    for color, paths in runs:
        svg.raw(f'<path d="{"".join(paths)}" stroke="{color}" stroke-width="{num(width)}" '
                f'stroke-opacity="{opacity}" fill="none" stroke-linecap="round"/>')


def title_plate(data: dict) -> tuple[str, str, str]:
    """Title plate on the black field: the name, the question and the neck-crossing wires in the front view."""
    svg = Svg(900, "dark", field=True)
    h = headline(data)
    svg.text(MARGIN + 4, 200, "The Price", 128, "#eeeeea", 600)
    svg.text(MARGIN + 4, 336, "of Thought", 128, "#eeeeea", 600)
    question = ["Is a fly's nervous system wired to keep", "its connections short, and what do its",
                "longest wires buy?"]
    for i, line in enumerate(question):
        svg.text(MARGIN + 10, 430 + i * 46, line, 36, "#eeeeea")
    facts = [
        f"{count(h['nodes'])} cell types, by side, of the adult male Drosophila CNS",
        f"{count(h['edges'])} connections, {count(h['neck_edges'])} of them crossing the neck",
    ]
    for i, line in enumerate(facts):
        svg.text(MARGIN + 10, 614 + i * 42, line, 28, "#a8a7a0")
    svg.text(MARGIN + 10, 744, f"The neck holds {pct(h['neck_cost_share'])} of the wire in "
                               f"{pct(h['neck_edge_share'])} of the connections.", 28, "#eeeeea", 500)
    svg.text(MARGIN + 10, 786, f"Placement costs {h['ratio']:.3f} times random placement.", 28, "#a8a7a0")

    front = data["front"]
    front_layer(svg, front, 960, 30, 790, "dark", width=1.4, opacity=0.62)
    svg.text(WIDTH - MARGIN, 872, f"{count(front['sample']['n'])} of the {count(front['crossing_edges'])} "
                                  "neck-crossing connections, coloured by length", 20, "#8f8e88", anchor="end")
    desc = (
        "The Price of Thought. Is a fly's nervous system wired to keep its connections short, and what do its "
        "longest wires buy? The male fruit fly central nervous system seen from the front on a black field, brain "
        f"above and nerve cord below, with {count(front['sample']['n'])} of its {count(front['crossing_edges'])} "
        "neck-crossing connections drawn as lines from dark red for the shortest to pale orange for the longest, "
        f"about a millimetre. The neck holds {pct(h['neck_cost_share'])} of the wire in {pct(h['neck_edge_share'])} "
        f"of the connections; the placement of cell types costs {h['ratio']:.3f} times random placement."
    )
    return svg.render("The Price of Thought", desc), desc, "plate-title.svg"


def stat_plate(data: dict, theme: str) -> tuple[str, str, str]:
    """Four headline numbers in a two-by-two grid."""
    svg = Svg(1100, theme)
    h = headline(data)
    col = [MARGIN, 928]
    tops = [60, 590]
    cells = [
        (f"{h['ratio']:.3f}×", "wire_ink",
         ["Wiring cost of the real placement", "against random placements"],
         [f"{h['within']:.3f}× when shuffled within brain or cord", f"Swaps still cut at least {pct(h['swap'])}"]),
        (pct(h["neck_cost_share"]), "ink",
         [f"Of all wire, in the {pct(h['neck_edge_share'])} of", "connections that cross the neck"],
         [f"Mean length {h['neck_mean']:.0f} µm, all edges {h['mean_length']:.0f} µm",
          f"Connective types among hubs: odds ratio {h['odds']:.2f}"]),
        (f"{h['value_ratio']:.2f}×", "ink",
         ["Flow lost by cutting the neck, against", "random wiring of the same length"],
         [f"{h['value_b2v']:.2f}× for brain-to-cord flow",
          f"Longest ordinary edges lose {count(h['lost_longest'])}, the neck {count(h['lost'])}"]),
        (f"{h['routes']:.3f}×", "ink",
         ["Rich-to-rich routes through the", "connective, against rewiring"],
         [f"{h['routes_low']:.3f}× at a 0.5% edge threshold",
          "A distance and cell-class model reproduces it"]),
    ]
    for i, (big, color, label, sub) in enumerate(cells):
        x, y = col[i % 2], tops[i // 2]
        svg.line(x, y, x + 768, y, "rule", 2)
        svg.text(x, y + 180, big, 128, color, 500, mono=True)
        for k, line in enumerate(label):
            svg.text(x, y + 258 + k * 56, line, 42, weight=600)
        for k, line in enumerate(sub):
            svg.text(x, y + 382 + k * 50, line, 32, "ink2")
    desc = (
        f"Results at a glance. The real placement of cell types costs {h['ratio']:.3f} times the wire of random "
        f"placements of the same positions, {h['within']:.3f} times when positions are shuffled only within brain or "
        f"nerve cord, and cost-reducing swaps still cut at least {pct(h['swap'])}. The {pct(h['neck_edge_share'])} "
        f"of connections that cross the neck hold {pct(h['neck_cost_share'])} of the wire. Cutting them removes "
        f"{h['value_ratio']:.2f} times the sensory-to-motor flow that random wiring of the same length removes, and "
        f"{h['value_b2v']:.2f} times for flow from brain to nerve cord. Rich-to-rich routes through the connective "
        f"are {h['routes']:.3f} times the rewired mean, and {h['routes_low']:.3f} times at a 0.5% edge threshold."
    )
    return svg.render("Results at a glance", desc), desc, f"stat-plate-{theme}.svg"


# Figures.

def figure_placement(data: dict, theme: str) -> tuple[str, str, str]:
    """Figure 1: real wiring cost relative to random placements, for every placement test, with the swap bound."""
    svg = Svg(760, theme)
    h = headline(data)
    p, e = data["placement"], data["economy"]["compartment_optimality"]
    heading(svg, 80, "The real placement against 1000 random placements of the same positions",
            "Wiring cost divided by the mean cost of the permutations. Blue marks the full range of the 1000 "
            "permutations; none came as low as the real placement.")
    rows = [
        ("Soma positions, all nodes shuffled (primary)", p["primary"]),
        ("Synapse-weighted cost", p["weighted"]),
        ("Shuffled only within brain or nerve cord", p["within_compartment"]),
        ("Synapse centroids as positions", p["synapse_positions"]),
        ("Brain connections only", e["brain"]),
        ("Nerve-cord connections only", e["vnc"]),
    ]
    px0, px1 = 720, 1560
    to_x = linear(0, 1.1, px0, px1)
    top, step = 250, 58
    bottom = top + step * (len(rows) - 1) + 40
    x_axis(svg, to_x, bottom, [0, 0.25, 0.5, 0.75, 1.0], ["0", "0.25", "0.5", "0.75", "1"], px0, px1,
           "Cost relative to the mean random placement", grid_top=top - 40)
    for i, (label, s) in enumerate(rows):
        y = top + i * step
        svg.text(MARGIN, y + 9, label, 26, "ink" if i == 0 else "ink2", 600 if i == 0 else 400)
        lo, hi = s["null_min"] / s["null_mean"], s["null_max"] / s["null_mean"]
        svg.rect(to_x(lo) - 2, y - 12, to_x(hi) - to_x(lo) + 4, 24, "null", rx=3, opacity=0.85)
        svg.dot(to_x(s["cost_ratio"]), y, 11, "wire", ring=3)
        svg.text(WIDTH - MARGIN, y + 9, f"{s['cost_ratio']:.3f}", 26, "ink" if i == 0 else "ink2",
                 500 if i == 0 else 400, anchor="end", mono=True)
    svg.line(to_x(h["swap_ratio"]) + 12, top, to_x(h["ratio"]) - 14, top, "wire", 2.5, dash="6 6")
    svg.dot(to_x(h["swap_ratio"]), top, 11, "wire", hollow=True, ring=3)
    svg.text(to_x(h["swap_ratio"]), top - 26, f"after swaps {h['swap_ratio']:.3f}", 22, "wire_ink", 500,
             anchor="middle", mono=True)
    note = (f"Hollow: the primary layout after 2,000,000 proposed swaps within compartments, each kept if it "
            f"shortened the wire. They cut {pct(h['swap'])} and had not converged, so the cheapest layout is lower "
            f"still.")
    for k, line in enumerate(wrap(note, 24, WIDTH - 2 * MARGIN)):
        svg.text(MARGIN, bottom + 122 + k * 34, line, 24, "ink2")
    listing = "; ".join(f"{label.lower()} {s['cost_ratio']:.3f}" for label, s in rows)
    desc = (
        f"Figure 1. Dot chart of wiring cost relative to the mean of 1000 random placements, one row per test: "
        f"{listing}. Every permutation range sits in a narrow band around 1, far to the right of every real value. "
        f"After greedy cost-reducing swaps the primary layout falls from {h['ratio']:.3f} to {h['swap_ratio']:.3f}, "
        f"a {pct(h['swap'])} saving that is a lower bound."
    )
    return svg.render("Figure 1. Placement against random placements", desc), desc, f"fig-placement-{theme}.svg"


def figure_distance(data: dict, theme: str) -> tuple[str, str, str]:
    """Figure 2: connection probability against distance for each pair of compartments."""
    svg = Svg(760, theme)
    table = data["distance"]
    dependence = data["economy"]["distance_dependence"]
    minima = data["economy"]["probability_minima"]
    heading(svg, 80, "Connection probability falls with distance, then rises again inside each compartment",
            "Share of ordered node pairs joined by an edge, in 20 µm bins with at least 1000 pairs.")
    px0, px1, py0, py1 = 150, 1040, 210, 620
    to_x = linear(0, 1000, px0, px1)
    to_y = linear(-4.6, -1.5, py1, py0)
    y_axis(svg, to_y, px0, [-4, -3, -2], ["0.0001", "0.001", "0.01"], py0, py1, grid_right=px1)
    x_axis(svg, to_x, py1, [0, 200, 400, 600, 800, 1000], ["0", "200", "400", "600", "800", "1000 µm"], px0, px1,
           "Distance between the two cell types' positions")
    series = [("brain-brain", "Brain to brain", "ink"), ("vnc-vnc", "Nerve cord to nerve cord", "null"),
              ("cross", "Across the neck", "wire")]
    ends = []
    for key, _, color in series:
        kept = table[table[f"pairs_{key}"] >= 1000]
        centres = (kept["bin_start_um"] + 10).to_numpy()
        probability = (kept[f"edges_{key}"] / kept[f"pairs_{key}"]).to_numpy()
        keep = probability > 0
        svg.polyline([to_x(v) for v in centres[keep]], [to_y(math.log10(v)) for v in probability[keep]], color, 3.5)
        ends.append(to_y(math.log10(probability[keep][-1])))
    for (_, label, color), y in zip(series, spread(ends, 34, py0, py1)):
        svg.text(px1 + 16, y + 8, label, 24, color, 600)
    kx = 1410
    svg.text(kx, 250, "Length constant, 0 to 600 µm", 24, "ink3")
    for i, (label, key) in enumerate((("All pairs", "all"), ("Brain to brain", "brain-brain"),
                                      ("Nerve cord", "vnc-vnc"), ("Across the neck", "cross"))):
        y = 300 + i * 44
        svg.text(kx, y, label, 24, "ink2")
        svg.text(WIDTH - MARGIN, y, f"{dependence[key]['length_constant_um']:.0f} µm", 24, "ink2", anchor="end",
                 mono=True)
    note = (f"Inside each compartment probability is lowest at {minima['brain-brain']['minimum_bin_um']:.0f} µm "
            f"(brain) and {minima['vnc-vnc']['minimum_bin_um']:.0f} µm (nerve cord), then rises: most of the longest "
            f"connections join the two sides of the body.")
    for k, line in enumerate(wrap(note, 24, WIDTH - MARGIN - kx)):
        svg.text(kx, 520 + k * 34, line, 24, "ink2")
    desc = (
        "Figure 2. Line chart, logarithmic vertical axis, of connection probability against distance from 0 to "
        f"1000 µm. All pairs together fall steadily, length constant {dependence['all']['length_constant_um']:.0f} "
        f"µm over the first 600 µm. Brain pairs fall to a minimum at {minima['brain-brain']['minimum_bin_um']:.0f} "
        f"µm and nerve-cord pairs at {minima['vnc-vnc']['minimum_bin_um']:.0f} µm, then rise again; pairs across the "
        f"neck start lower and fall with a length constant of {dependence['cross']['length_constant_um']:.0f} µm."
    )
    return svg.render("Figure 2. Connection probability and distance", desc), desc, f"fig-distance-{theme}.svg"


def figure_cost(data: dict, theme: str) -> tuple[str, str, str]:
    """Figure 3: share of edges against share of wiring cost for the connective and hub edges."""
    svg = Svg(620, theme)
    shares = data["economy"]["cost_share"]
    heading(svg, 80, "The neck holds a quarter of the wire in under a tenth of the connections",
            "Share of all connections and share of total wiring length. The first three groups overlap; the last "
            "holds connections in none of them.")
    labels = {"neck-crossing": "Crossing the neck", "connective-incident": "Any descending or ascending edge",
              "high-degree-incident": f"Touching a hub (degree ≥ {shares['degree_threshold']:.0f})",
              "none of these": "None of these"}
    px0, px1 = 640, 1400
    to_x = linear(0, 0.6, px0, px1)
    top = 250
    svg.text(WIDTH - MARGIN, top - 50, "Mean length", 22, "ink3", anchor="end")
    for i, row in enumerate(shares["rows"]):
        y = top + i * 76
        svg.text(MARGIN, y + 14, labels[row["label"]], 26, "ink" if i == 0 else "ink2", 600 if i == 0 else 400)
        svg.rect(px0, y - 14, to_x(row["edge_share"]) - px0, 18, "rule_strong", rx=2)
        svg.rect(px0, y + 8, to_x(row["cost_share"]) - px0, 18, "wire", rx=2)
        svg.text(to_x(row["edge_share"]) + 10, y + 2, pct(row["edge_share"]), 20, "ink3", mono=True)
        svg.text(to_x(row["cost_share"]) + 10, y + 25, pct(row["cost_share"]), 20, "wire_ink", 500, mono=True)
        svg.text(WIDTH - MARGIN, y + 14, f"{row['mean_length_um']:.0f} µm", 24, "ink2", anchor="end", mono=True)
    y = top + 4 * 76 + 10
    svg.rect(px0, y, 30, 14, "rule_strong", rx=2)
    svg.text(px0 + 42, y + 13, "share of connections", 22, "ink2")
    svg.rect(px0 + 320, y, 30, 14, "wire", rx=2)
    svg.text(px0 + 362, y + 13, "share of wiring length", 22, "ink2")
    neck = shares["rows"][0]
    desc = (
        "Figure 3. Paired bar chart of the share of connections and the share of total wiring length. Neck-crossing "
        f"connections: {pct(neck['edge_share'])} of connections, {pct(neck['cost_share'])} of wire, mean "
        f"{neck['mean_length_um']:.0f} µm. " + " ".join(
            f"{labels[r['label']]}: {pct(r['edge_share'])} of connections, {pct(r['cost_share'])} of wire."
            for r in shares["rows"][1:])
    )
    return svg.render("Figure 3. Where the wire goes", desc), desc, f"fig-cost-{theme}.svg"


def figure_routes(data: dict, theme: str) -> tuple[str, str, str]:
    """Figure 4: rich-to-rich routing ratio by richness threshold and by edge threshold."""
    svg = Svg(720, theme)
    curve = data["richclub"]["threshold_curve"]
    rows = data["robustness"]["thresholds"]
    heading(svg, 80, "Rich-to-rich routes through the connective depend on what counts as rich and as a connection",
            "Real routes divided by the mean of 1000 layer-preserving rewirings. Filled: one-sided p < 0.05; hollow: "
            "not significant. Blue: central 95% of the rewirings.")
    to_y = linear(0.6, 1.8, 600, 250)
    panels = [
        (160, 800, "Top share of partners counted as rich, edge threshold 1%",
         [(f"{100 * c['top_fraction']:g}%", c["ratio"], c["ratio_lo"], c["ratio_hi"], c["p_value"]) for c in curve]),
        (1040, 1640, "Edge threshold, top 10% counted as rich",
         [(f"{100 * r['fraction']:g}%", r["routes"]["total"]["ratio"],
           1 - 1.96 * r["routes"]["total"]["null_sd"] / r["routes"]["total"]["null_mean"],
           1 + 1.96 * r["routes"]["total"]["null_sd"] / r["routes"]["total"]["null_mean"],
           r["routes"]["total"]["p_value"]) for r in rows]),
    ]
    for px0, px1, title, points in panels:
        y_axis(svg, to_y, px0, [0.6, 1.0, 1.4, 1.8], ["0.6", "1.0", "1.4", "1.8"], 250, 600, grid_right=px1)
        svg.line(px0, to_y(1), px1, to_y(1), "rule_strong", 2)
        xs = [px0 + (k + 0.5) * (px1 - px0) / len(points) for k in range(len(points))]
        svg.polygon(xs + xs[::-1], [to_y(p[3]) for p in points] + [to_y(p[2]) for p in points][::-1], "null", 0.22)
        svg.polyline(xs, [to_y(p[1]) for p in points], "wire", 2.5)
        for x, (label, ratio, _, _, p) in zip(xs, points):
            svg.dot(x, to_y(ratio), 10, "wire", hollow=p >= 0.05, ring=3)
            svg.text(x, to_y(ratio) - 22, f"{ratio:.2f}", 20, "ink2", anchor="middle", mono=True)
            svg.text(x, 636, label, 22, "ink2", anchor="middle", mono=True)
        svg.line(px0, 600, px1, 600, "axis", 2)
        svg.text((px0 + px1) / 2, 680, title, 24, "ink2", anchor="middle")
    listing = ", ".join(f"{100 * c['top_fraction']:g}% {c['ratio']:.2f}" for c in curve)
    by_edge = ", ".join(f"{100 * r['fraction']:g}% {r['routes']['total']['ratio']:.3f}" for r in rows)
    significant = ", ".join(f"{100 * c['top_fraction']:g}%" for c in curve if c["p_value"] < 0.05)
    desc = (
        "Figure 4. Two dot charts of the ratio of real rich-to-rich routes through the connective to the rewired "
        f"mean. By share of partners counted as rich: {listing}; significant at {significant} only. By edge "
        f"threshold: {by_edge}; the excess vanishes at 0.5% and grows as weak connections are dropped."
    )
    return svg.render("Figure 4. Rich-to-rich routing", desc), desc, f"fig-routes-{theme}.svg"


def figure_value(data: dict, theme: str) -> tuple[str, str, str]:
    """Figure 5: flow lost by cutting the neck against cost-matched, count-matched and longest-edge removals."""
    svg = Svg(960, theme)
    value = data["value"]
    nulls = data["value_nulls"]
    intact, real = value["intact"], value["real"]
    heading(svg, 80, "Cutting the neck costs less flow than random wiring of the same length, except from brain to cord",
            "Sensory-to-motor flow capacity lost, in edge-disjoint paths. Histograms: 1000 random sets of ordinary "
            "connections matched on total length (filled) or on number of connections (outline).")
    rows = [("flow", "All sensory to motor"), ("flow_brain_to_vnc", "Brain sensory to nerve-cord motor"),
            ("flow_vnc_to_brain", "Nerve-cord sensory to brain motor")]
    px0, px1 = 560, 1640
    for i, (metric, label) in enumerate(rows):
        base = 380 + i * 210
        cost = intact[metric] - nulls.loc[nulls["family"] == "crossing_cost", metric].to_numpy()
        by_count = intact[metric] - nulls.loc[nulls["family"] == "crossing_count", metric].to_numpy()
        cut = intact[metric] - real["crossing"][metric]
        longest = intact[metric] - real["longest"][metric]
        top = max(cost.max(), by_count.max(), cut, longest) * 1.08
        to_x = linear(0, top, px0, px1)
        to_y = linear(0, 1, base, base - 110)
        svg.text(MARGIN, base - 62, label, 26, "ink" if i == 0 else "ink2", 600 if i == 0 else 400)
        svg.text(MARGIN, base - 26, f"{count(intact[metric])} intact", 22, "ink3", mono=True)
        for values, filled in ((cost, True), (by_count, False)):
            xs, ys = histogram_outline(values, np.linspace(values.min(), values.max() + 1, 26))
            if filled:
                svg.polygon([to_x(v) for v in xs], [to_y(v) for v in ys], "null", 0.55)
            else:
                svg.polyline([to_x(v) for v in xs], [to_y(v) for v in ys], "null", 2)
        svg.line(to_x(longest), base - 118, to_x(longest), base, "ink2", 2.5, dash="5 5")
        svg.line(to_x(cut), base - 124, to_x(cut), base, "wire", 4)
        at_cut, at_longest = spread([to_x(cut), to_x(longest)], 190, px0 + 90, px1 - 90)
        svg.text(at_cut, base - 136, f"neck {count(cut)}", 22, "wire_ink", 500, anchor="middle", mono=True)
        svg.text(at_longest, base - 136, f"longest {count(longest)}", 22, "ink2", anchor="middle", mono=True)
        ticks = list(np.linspace(0, top, 5))
        x_axis(svg, to_x, base, ticks, [count(t) for t in ticks], px0, px1)
    svg.text(MARGIN, 930, "Orange: the 36,943 neck-crossing connections cut. Dashed: the longest ordinary connections, "
                          "taken until their total length matches the neck.", 22, "ink2")
    fam = value["families"]
    desc = (
        "Figure 5. Three rows of histograms of sensory-to-motor flow lost under random removals, with the loss from "
        f"cutting the neck marked. All flow: the cut removes {count(intact['flow'] - real['crossing']['flow'])}, "
        f"length-matched random sets {fam['crossing_cost']['flow']['null_mean']:.0f} on average (ratio "
        f"{fam['crossing_cost']['flow']['ratio']:.2f}), count-matched sets "
        f"{fam['crossing_count']['flow']['null_mean']:.0f}, the longest ordinary edges "
        f"{count(intact['flow'] - real['longest']['flow'])}. Brain to nerve cord: ratio "
        f"{fam['crossing_cost']['flow_brain_to_vnc']['ratio']:.2f}, the cut beyond every random set. Nerve cord to "
        f"brain: ratio {fam['crossing_cost']['flow_vnc_to_brain']['ratio']:.2f}."
    )
    return svg.render("Figure 5. Value of the connective", desc), desc, f"fig-value-{theme}.svg"


def figure_price(data: dict, theme: str) -> tuple[str, str, str]:
    """Figure 6: each connective cell type's neck-crossing wire length against the flow it carries alone."""
    svg = Svg(820, theme)
    nodes = data["price_nodes"]
    tests = data["price"]["tests"]
    heading(svg, 80, "More wire does not buy a cell type more flow",
            "Each dot is a descending or ascending cell type on one side: the total length of its neck-crossing "
            "connections, and the flow lost in its own direction when those alone are removed.")
    panels = [("descending", "Descending, brain to nerve cord", 110, 820),
              ("ascending", "Ascending, nerve cord to brain", 1000, 1700)]
    top = max(18, int(nodes["value"].max()) + 1)
    to_y = linear(0, top, 680, 300)
    floor_mm = 0.5
    for group, title, px0, px1 in panels:
        part = nodes[nodes["direction"] == group]
        to_x = linear(math.log10(floor_mm), math.log10(200), px0, px1)

        def x_of(price_um: float) -> float:
            return to_x(math.log10(max(price_um / 1000, floor_mm)))

        y_axis(svg, to_y, px0, [0, 5, 10, 15], ["0", "5", "10", "15"], 300, 680, grid_right=px1)
        x_axis(svg, to_x, 680, [math.log10(v) for v in (1, 10, 100)], ["1 mm", "10 mm", "100 mm"], px0, px1)
        for row in part[part["value"] == 0].itertuples():
            svg.circle(x_of(row.price_um), to_y(0), 3.5, "ink3", opacity=0.35)
        for row in part[part["value"] > 0].itertuples():
            svg.circle(x_of(row.price_um), to_y(row.value), 5, "wire", opacity=0.6)
        t = tests[group]
        svg.text(px0, 222, title, 26, weight=600)
        svg.text(px0, 256, f"ρ {signed(t['spearman_rho'], 3)}, given edges {signed(t['partial_rho'], 3)}; "
                           f"{t['zero_value']} of {count(t['n'])} lose no flow", 22, "ink2", mono=True)
        for row in (part.loc[part["price_um"].idxmax()], part.loc[part["value"].idxmax()]):
            x, y = x_of(row["price_um"]), to_y(row["value"])
            svg.circle(x, y, 7, "wire", stroke="ink", stroke_width=2)
            svg.text(x - 14, y - 14, row["node"].replace("|", " "), 20, "ink", anchor="end", mono=True)
    svg.text(WIDTH / 2, 770, "Horizontal: total length of the type's neck-crossing connections, log scale. Vertical: "
                             "flow lost, in edge-disjoint paths.", 22, "ink2", anchor="middle")
    desc = (
        "Figure 6. Two scatter plots, descending and ascending cell types, of neck-crossing wire length (logarithmic) "
        "against the flow lost when that wire alone is removed. Most dots lie on zero: "
        f"{tests['descending']['zero_value']} of {tests['descending']['n']} descending and "
        f"{tests['ascending']['zero_value']} of {count(tests['ascending']['n'])} ascending types lose no flow. Rank "
        f"correlation {tests['descending']['spearman_rho']:.3f} for descending types, "
        f"{tests['descending']['partial_rho']:.3f} once the number of connections is controlled for; "
        f"{signed(tests['ascending']['spearman_rho'], 3)} for ascending types."
    )
    return svg.render("Figure 6. Price and value by cell type", desc), desc, f"fig-price-{theme}.svg"


GENERATIVE_LABELS = {
    "in_degree_sd": "In-degree, SD",
    "in_degree_max": "In-degree, maximum",
    "out_degree_sd": "Out-degree, SD",
    "out_degree_max": "Out-degree, maximum",
    "total_cost_um": "Total wiring length",
    "median_length_um": "Median connection length",
    "cross_compartment_fraction": "Share joining brain and cord",
    "reciprocity": "Reciprocity",
    "transitivity": "Transitivity",
    "flow": "Sensory-to-motor flow",
    "pairs": "Reachable sensory-motor pairs",
    "neck_crossing_edges": "Neck-crossing connections",
    "rich_routes": "Rich-to-rich routes",
}


def reproduced_count(models: dict, key: str) -> int:
    return sum(p["reproduced"] for p in models[key]["properties"].values())


def figure_generative(data: dict, theme: str) -> tuple[str, str, str]:
    """Figure 7: each real graph property against the 50 synthetic graphs of each generative model."""
    models = data["comparison"]["models"]
    fits = data["fits"]["models"]
    svg = Svg(300 + 50 * len(GENERATIVE_LABELS) + 120, theme)
    heading(svg, 80, "A distance and cell-class model reproduces the rich-to-rich routes and little else",
            "Real value divided by the synthetic mean, log scale. Blue: central 95% of 50 synthetic graphs; orange "
            f"dots fall outside it. Model G uses distance, compartment and cell class (pseudo-R² "
            f"{fits['G']['pseudo_r2_mcfadden']:.3f}); G+deg adds degree ({fits['G_deg']['pseudo_r2_mcfadden']:.3f}).")
    panels = [("G", "Model G", 620, 1120), ("G_deg", "Model G+deg", 1220, 1700)]
    top = 300
    bottom = top + 50 * (len(GENERATIVE_LABELS) - 1) + 30
    bound = 1 / 40
    for key, title, px0, px1 in panels:
        to_x = linear(math.log10(1 / 32), math.log10(32), px0, px1)
        svg.text(px0, top - 50, f"{title}: {reproduced_count(models, key)} of {len(GENERATIVE_LABELS)} reproduced",
                 24, weight=600)
        ticks = [1 / 16, 1 / 4, 1, 4, 16]
        x_axis(svg, to_x, bottom, [math.log10(t) for t in ticks], ["1/16", "1/4", "1", "4", "16"], px0, px1,
               grid_top=top - 24)
        svg.line(to_x(0), top - 24, to_x(0), bottom, "rule_strong", 2)
        for i, prop in enumerate(GENERATIVE_LABELS):
            p = models[key]["properties"][prop]
            y = top + i * 50
            mean = p["synthetic_mean"]
            lo, hi = (math.log10(min(max(v / mean, bound), 1 / bound)) for v in p["interval_95"])
            svg.rect(to_x(lo) - 2, y - 9, to_x(hi) - to_x(lo) + 4, 18, "null", rx=3, opacity=0.8)
            ratio = p["real"] / mean
            x = min(max(to_x(math.log10(min(max(ratio, bound), 1 / bound))), px0), px1)
            svg.dot(x, y, 8, "ink" if p["reproduced"] else "wire", ring=2)
            if ratio >= 3 or ratio <= 1 / 3:
                svg.text(x + (-16 if ratio >= 3 else 16), y + 7, f"{ratio:.3g}×", 20, "wire_ink", 500,
                         anchor="end" if ratio >= 3 else "start", mono=True)
    for i, prop in enumerate(GENERATIVE_LABELS):
        svg.text(MARGIN, top + i * 50 + 8, GENERATIVE_LABELS[prop], 24, "ink2")
    svg.text(MARGIN, bottom + 36, "Real ÷ synthetic mean", 22, "ink3", mono=True)
    g = models["G"]["properties"]
    desc = (
        "Figure 7. For thirteen graph properties, the real value relative to the mean of 50 synthetic graphs from two "
        f"logistic models, with the synthetic 95% range. Model G reproduces {reproduced_count(models, 'G')} "
        f"properties, including rich-to-rich routes (real {g['rich_routes']['real']:.0f}, synthetic mean "
        f"{g['rich_routes']['synthetic_mean']:.0f}); model G+deg reproduces {reproduced_count(models, 'G_deg')}. The "
        f"real graph has {g['reciprocity']['real'] / g['reciprocity']['synthetic_mean']:.0f} times model G's "
        f"reciprocity and {g['transitivity']['real'] / g['transitivity']['synthetic_mean']:.0f} times its "
        f"transitivity."
    )
    return svg.render("Figure 7. What the generative models reproduce", desc), desc, f"fig-generative-{theme}.svg"


def methods_pipeline(data: dict, theme: str) -> tuple[str, str, str]:
    """The analysis pipeline as eight numbered steps in two rows."""
    svg = Svg(660, theme)
    h = headline(data)
    steps = [
        ("Data", f"{count(TYPED_NEURONS)} typed neurons", "neuPrint male-cns:v1.0"),
        ("Spatial graph", f"{count(h['nodes'])} nodes by side", "build_spatial_graph.py"),
        ("Pre-registration", "3 commits before results", ", ".join(PREREGISTRATION_COMMITS)),
        ("Placement", "1000 permutations, swaps", "spatial_permutation_test.py"),
        ("Rich club", "1000 layer rewirings", "connective_richclub.py"),
        ("Value", "1000 cost-matched sets", "connective_value.py"),
        ("Generative model", "4 fits, 100 graphs", "generative_model.py"),
        ("Checks", "3 thresholds, verify", "make verify"),
    ]
    box_w, box_h = 370, 218
    xs = [65 + i * 420 for i in range(4)]
    ys = [61, 381]
    paths, heads = [], []
    for y in ys:
        for i in range(3):
            x = xs[i] + box_w + 1
            paths.append(f"M{x} {y + 109}H{x + 36}")
            heads.append(f"M{x + 45} {y + 109}L{x + 35} {y + 104}V{y + 114}Z")
    paths.append("M1510 280V318A12 12 0 0 1 1498 330H262A12 12 0 0 0 250 342V368")
    heads.append("M250 377L245 367H255Z")
    opacity = ' opacity="0.7"' if theme == "dark" else ""
    svg.raw(
        f'<g{opacity}><path d="{"".join(paths)}" fill="none" stroke="{svg.c("rule_strong")}" stroke-width="2"/>'
        f'<path d="{"".join(heads)}" fill="{svg.c("rule_strong")}"/></g>'
    )
    for k, (title, value, module) in enumerate(steps):
        x, y = xs[k % 4], ys[k // 4]
        svg.rect(x, y, box_w, box_h, "plate", rx=11, stroke="rule")
        svg.text(x + 22, y + 52, str(k + 1), 30, "ink3", 500, mono=True)
        svg.text(x + 56, y + 52, title, 26, weight=600)
        svg.text(x + 22, y + 116, value, 28)
        svg.text(x + 22, y + 170, module, 20, "ink2", mono=True)
    desc = (
        f"The analysis pipeline in eight steps: 1 data, {count(TYPED_NEURONS)} typed neurons from neuPrint "
        f"male-cns:v1.0; 2 spatial graph, {count(h['nodes'])} cell types by side and {count(h['edges'])} connections; "
        f"3 pre-registration in commits {', '.join(PREREGISTRATION_COMMITS)} before any result; 4 placement, 1000 "
        "permutations and a swap search; 5 rich club, 1000 layer-preserving rewirings; 6 value, 1000 cost-matched "
        "removals; 7 generative model, four logistic fits and 100 synthetic graphs; 8 checks, three more edge "
        "thresholds and a verification suite that recomputes every statistic."
    )
    return svg.render("The analysis pipeline in eight steps", desc), desc, f"methods-pipeline-{theme}.svg"


THEMED = (stat_plate, figure_placement, figure_distance, figure_cost, figure_routes, figure_value, figure_price,
          figure_generative, methods_pipeline)


def build_all(data: dict, out_dir: Path) -> list[Path]:
    """Write every README asset into ``out_dir`` and return the paths written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    jobs: list[tuple[str, str, str]] = [title_plate(data)]
    for build in THEMED:
        for theme in THEMES:
            jobs.append(build(data, theme))
    for svg, _, name in jobs:
        path = out_dir / name
        path.write_text(svg, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    for path in build_all(load_inputs(), args.out):
        print(f"Wrote {path} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
