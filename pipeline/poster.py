"""Render the one-page poster of the study at print size, and a smaller preview for the README."""

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import to_rgb  # noqa: E402
from matplotlib.font_manager import FontProperties, fontManager  # noqa: E402
from matplotlib.patches import Circle, PathPatch, Rectangle  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402
from PIL import Image  # noqa: E402

from pipeline import readme_assets as ra  # noqa: E402
from pipeline.common import ASSETS, RESULTS  # noqa: E402
from pipeline.qr_code import encode  # noqa: E402

WIDTH, HEIGHT = 3508, 4960
PRINT_DPI = 300
PREVIEW_WIDTH = 880
MARGIN = 128
GUTTER = 88
COLUMNS = 3
BAND_HEIGHT = 1270
METHODS_HEIGHT = 230
LEDE_TOP = BAND_HEIGHT + METHODS_HEIGHT + 80
COLUMN_TOP = 2040
CHECKS_TOP = 4050
FOOTER_TOP = 4600
OUT_DIR = ASSETS / "readme"
POSTER_PATH = OUT_DIR / "price-of-thought-poster.png"
PREVIEW_PATH = OUT_DIR / "poster-preview.png"

REPO_URL = "https://github.com/dhruvin-sarkar/price-of-thought"
AUTHOR = "Dhruvin Sarkar"

LIGHT, DARK = ra.THEMES["light"], ra.THEMES["dark"]
FIELD = "#000000"
FIELD_TISSUE = DARK["track"]
FIELD_RULE = DARK["rule"]
FIELD_EDGE = DARK["rule_strong"]
FIELD_INK = DARK["ink"]
FIELD_INK_2 = DARK["ink2"]
WIRE_GLOW = DARK["wire"]
PAPER = LIGHT["ground"]
WASH = LIGHT["track"]
RULE = LIGHT["rule"]
RULE_STRONG = LIGHT["rule_strong"]
INK = LIGHT["ink"]
INK_2 = LIGHT["ink2"]
INK_3 = LIGHT["ink3"]
WIRE = LIGHT["wire"]
WIRE_INK = LIGHT["wire_ink"]
NULL = LIGHT["null"]

# Poster figures share their numbers with the README figures they redraw. The sheet holds nine; the README
# figures left off it are named in the captions of the panels that stand in for them.
FIGURE_LAYOUT = (("placement", "distance", "cost"), ("atlas", "concentration", "routes"),
                 ("value", "price", "tradeoff"))
FIGURE_NUMBERS = {"placement": 1, "distance": 2, "cost": 3, "atlas": 4, "concentration": 5, "routes": 6,
                  "value": 7, "price": 8, "tradeoff": 11}
# Each column carries a heading before the figure it names; the others continue the heading above them.
COLUMN_HEADINGS = {"placement": "What the layout costs", "atlas": "Where the wire goes",
                   "routes": "The connective and its hubs", "value": "What the connective buys",
                   "tradeoff": "What length buys"}
QUESTION = (
    "Nervous systems are thought to place their parts so as to keep wiring short,^2^ and in the human brain the "
    "best-connected regions are joined by long, costly connections that carry much of the traffic.^3^ The complete "
    "connectome of a male fruit fly, brain and nerve cord together,^1^ was tested for both. **Its cell types are "
    "placed economically and far from optimally; the neck connective joins its hubs, and buys less routing per "
    "unit of wire than ordinary wiring does.**"
)
REFERENCES = (
    "Berg S, et al. (2026). Sexual dimorphism in the complete *Drosophila* male central nervous system connectome. "
    "*Cell* 189(18):5504–5526.e15. doi:10.1016/j.cell.2026.08.015",
    "Cherniak C (1994). Component placement optimization in the brain. *J Neurosci* 14(4):2418–2427. "
    "doi:10.1523/JNEUROSCI.14-04-02418.1994",
    "van den Heuvel MP, Kahn RS, Goñi J, Sporns O (2012). High-cost, high-capacity backbone for global brain "
    "communication. *PNAS* 109(28):11372–11377. doi:10.1073/pnas.1203593109",
    "Lin A, et al. (2024). Network statistics of the whole-brain connectome of *Drosophila*. *Nature* "
    "634(8032):153–165. doi:10.1038/s41586-024-07968-y",
)
NBSP = " "
TICK = 25
LABEL = 27
CAPTION = 27


# Layout and formatting

def column_edges(width: float, margin: float, gutter: float, n: int) -> list[tuple[float, float]]:
    """Left and right edge of each of ``n`` equal columns between the margins."""
    column = (width - 2 * margin - (n - 1) * gutter) / n
    return [(margin + i * (column + gutter), margin + i * (column + gutter) + column) for i in range(n)]


def split_cells(x0: float, x1: float, n: int, gap: float) -> list[tuple[float, float]]:
    """Divide [x0, x1] into ``n`` equal cells separated by ``gap``."""
    cell = (x1 - x0 - (n - 1) * gap) / n
    return [(x0 + i * (cell + gap), x0 + i * (cell + gap) + cell) for i in range(n)]


def linear(d0: float, d1: float, r0: float, r1: float):
    """Map the data interval [d0, d1] onto the drawing interval [r0, r1]."""
    return lambda v: r0 + (np.asarray(v, dtype=float) - d0) / (d1 - d0) * (r1 - r0)


def reading_order(layout=FIGURE_LAYOUT, numbers=None) -> list[int]:
    """Figure numbers down each column and then across; raises ValueError if they do not rise."""
    numbers = FIGURE_NUMBERS if numbers is None else numbers
    ordered = [numbers[key] for column in layout for key in column]
    if ordered != sorted(ordered) or len(set(ordered)) != len(ordered):
        raise ValueError(f"figure numbers out of reading order: {ordered}")
    return ordered


def wrap_widths(widths: list[float], space: float, limit: float) -> list[list[int]]:
    """Greedy line breaks: indices of the words on each line, given word widths and the space width."""
    lines: list[list[int]] = []
    current: list[int] = []
    used = 0.0
    for i, w in enumerate(widths):
        needed = w if not current else used + space + w
        if current and needed > limit:
            lines.append(current)
            current, used = [i], w
        else:
            current.append(i)
            used = needed
    if current:
        lines.append(current)
    return lines


# Words break at ordinary spaces only, so a no-break space keeps "p = 0.05" on one line.
MARKUP = re.compile(r"\*\*|\*|\^[^^]*\^|[ \t\r\n]+|[^*^ \t\r\n]+")


def parse_markup(text: str) -> list[list[tuple[str, str]]]:
    """Words of ``text`` as runs of (text, style); ``**bold**`` and ``*italic*`` toggle, ``^1^`` is a superscript."""
    words: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    bold = italic = False
    for token in MARKUP.findall(text):
        if token == "**":
            bold = not bold
        elif token == "*":
            italic = not italic
        elif token[0] in " \t\r\n":
            if current:
                words.append(current)
                current = []
        elif token.startswith("^"):
            current.append((token[1:-1], "sup"))
        else:
            current.append((token, "bold" if bold else "italic" if italic else "regular"))
    if current:
        words.append(current)
    return words


def hypotheses(data: dict) -> list[tuple[str, str, bool]]:
    """Label, statement and outcome of every pre-registered hypothesis, read from the results."""
    h = ra.headline(data)
    economy = data["economy"]
    richclub = data["richclub"]
    value = data["value"]["families"]["crossing_cost"]["flow"]
    price = data["price"]
    distance = economy["distance_dependence"]["all"]
    return [
        ("H", f"Placement is cheaper than permuted positions ({h['ratio']:.3f}×)",
         data["placement"]["primary"]["significant"]),
        ("H1", f"Rich-to-rich routes exceed rewiring ({h['routes']:.3f}×)",
         richclub["routes_top10"]["total"]["significant"]),
        ("H2", f"Connective partners are enriched for hubs ({richclub['endpoint_enrichment']['ratio']:.2f}×)",
         richclub["endpoint_enrichment"]["significant"]),
        ("H3", f"Connective types are over-represented among hubs (odds ratio {h['odds']:.2f})",
         richclub["whole_cns_membership"]["significant"]),
        ("H4", f"Cutting the neck costs more flow than equal-length wiring ({value['ratio']:.2f}×)",
         value["significant"]),
        ("H5", f"Connection probability falls with distance (ρ = {ra.signed(distance['spearman_rho'], 3)})",
         distance["significant"]),
        ("H6", f"Swaps lower the cost by more than 1% ({ra.pct(h['swap'])})", economy["local_optimum"]["supported"]),
        ("H7", f"Edges of hubs are longer ({economy['cost_share']['mean_length_high_um']:.0f} against "
               f"{economy['cost_share']['mean_length_other_um']:.0f} µm)", economy["cost_share"]["significant"]),
        ("H8", f"Longer edges carry more shortest paths (ρ = {economy['length_traffic']['rho_all']:.3f})",
         economy["length_traffic"]["significant"]),
        ("H9", f"Cable length tracks soma-to-output distance (ρ = {data['cable']['spearman_rho']:.3f})",
         data["cable"]["significant"]),
        ("H10", "A type's wire length predicts its flow, in both directions", price["h10_supported"]),
        ("H10b", f"The same at a given number of connections (partial ρ = "
                 f"{price['tests']['descending']['partial_rho']:.3f})", price["h10b_supported"]),
        ("H11", "Placement, routes and hubs hold at 0.5%, 2% and 5%", data["robustness"]["h11_supported"]),
    ]


def limitations(data: dict) -> list[tuple[str, str]]:
    """Lead and text of each limitation on the poster."""
    atlas = data["atlas"]["totals"]
    return [
        ("Cell-type resolution.", "Types sit at the centroid of their cell bodies, and straight lines between "
                                  "centroids stand in for processes that follow tracts."),
        ("Nearest surface, not arbor.", f"A type is charged to the neuropil nearest its centroid, a median "
                                        f"{atlas['median_distance_to_surface_um']:.1f} µm away, not to the "
                                        "regions its branches enter."),
        ("One edge threshold.", "Rich-to-rich routing vanishes at 0.5%; placement and hubs hold from 0.5% to 5%."),
        ("Routes, not signal.", "Flow counts disjoint paths, which rewards many short connections over a few "
                                "long ones."),
        ("A bounded tail.", "The length distribution is not a power law: a lognormal and a truncated power law "
                            "both fit its upper tail better."),
        ("One animal.", "A single male fly and one static reconstruction, not peer reviewed."),
    ]


def lede_findings(data: dict) -> list[tuple[str, str, str, str]]:
    """Label, display number, body and colour of each headline finding, read from the results."""
    atlas, concentration = data["atlas"], data["concentration"]
    tested = [row for row in atlas["neuropils"] if "cost_ratio" in row]
    beyond = sum(1 for row in tested if row["n_at_or_below_real"] == 0)
    top = atlas["neuropils"][0]
    curves = concentration["lorenz"]
    families = data["value"]["families"]["crossing_cost"]
    return [
        ("Where the wire ends", ra.pct(top["wire_share"]),
         f"of the wiring budget ends in the gnathal ganglia ({top['neuropil']}), more than in any other region. "
         f"Inside all {len(tested)} regions large enough to test, the cell types are packed below their own "
         f"permuted mean, {beyond} of them below every one of the 1000 permutations. Exploratory, and run "
         f"after the registered tests.", INK),
        ("How unevenly it is spread", ra.pct(curves["all"]["top_shares"]["0.1"]),
         f"of the wire lies in the longest tenth of the connections, a Gini coefficient of "
         f"{curves['all']['gini']:.3f}. The neck-crossing connections are the most uniform set of all, at "
         f"{curves['across the neck']['gini']:.3f}: long, and nearly all of a length. Exploratory, and run "
         f"after the registered tests.", INK),
        ("What the longest wire buys", f"{families['flow']['ratio']:.2f}×",
         f"the sensory-to-motor routing that random ordinary wiring of the same total length carries. This was "
         f"registered to exceed 1 and does not; only from brain to nerve cord does the neck carry more, at "
         f"{families['flow_brain_to_vnc']['ratio']:.2f}×.", WIRE_INK),
    ]


# Fonts

# DejaVu ships with matplotlib and supplies glyphs the project faces lack, such as the Greek rho.
FALLBACK_FAMILIES = {"sans": "DejaVu Sans", "mono": "DejaVu Sans Mono"}
_families: dict[str, tuple[str, int]] = {}


def load_fonts() -> dict[str, tuple[str, int]]:
    """Register the project's static Archivo and Spline Sans Mono files; returns (family, weight) by text role."""
    _families.clear()
    for role, path in ra.project_fonts().items():
        fontManager.addfont(str(path))
        entry = next(f for f in fontManager.ttflist if Path(f.fname) == Path(path))
        _families[role] = (entry.name, entry.weight)
    return dict(_families)


def font(role: str, size: float) -> FontProperties:
    """FontProperties for a text role at ``size`` pixels, falling back glyph by glyph to DejaVu."""
    fallback = FALLBACK_FAMILIES["mono" if role.startswith("mono") else "sans"]
    if role in _families:
        family, weight = _families[role]
        return FontProperties(family=[family, fallback], weight=weight, size=size)
    return FontProperties(family=fallback, size=size, weight="bold" if role == "sans_bold" else "normal")


STYLE_ROLES = {"regular": "sans", "bold": "sans_bold", "italic": "sans", "sup": "sans"}


@dataclass
class Frame:
    """A chart area with its data scales."""

    x0: float
    y0: float
    x1: float
    y1: float
    sx: object
    sy: object


class Sheet:
    """The poster canvas: one unit per pixel, origin at the top left, text placed on its baseline."""

    def __init__(self, width: int, height: int, ground: str = PAPER) -> None:
        self.fig = plt.figure(figsize=(width / 72, height / 72), dpi=72, facecolor=ground)
        self.ax = self.fig.add_axes((0, 0, 1, 1))
        self.ax.set_xlim(0, width)
        self.ax.set_ylim(height, 0)
        self.ax.axis("off")
        self._renderer = self.fig.canvas.get_renderer()
        self._widths: dict[tuple, float] = {}

    def width_of(self, s: str, size: float, role: str) -> float:
        key = (s, size, role)
        if key not in self._widths:
            self._widths[key] = self._renderer.get_text_width_height_descent(s, font(role, size), ismath=False)[0]
        return self._widths[key]

    def text(self, x, y, s, size, role="sans", color=INK, ha="left", zorder=6):
        return self.ax.text(x, y, s, fontproperties=font(role, size), color=color, ha=ha, va="baseline",
                            zorder=zorder)

    def rect(self, x0, y0, x1, y1, color, alpha=1.0, zorder=1) -> None:
        self.ax.add_patch(Rectangle((min(x0, x1), min(y0, y1)), abs(x1 - x0), abs(y1 - y0), facecolor=color,
                                    edgecolor="none", alpha=alpha, zorder=zorder))

    def line(self, xs, ys, color, width=2.0, dashes=None, alpha=1.0, zorder=3, cap="butt") -> None:
        (artist,) = self.ax.plot(xs, ys, color=color, linewidth=width, alpha=alpha, zorder=zorder,
                                 solid_capstyle=cap, solid_joinstyle="round")
        if dashes:
            artist.set_linestyle((0, dashes))

    def fill(self, xs, ys, color, alpha=1.0, zorder=2) -> None:
        self.ax.fill(xs, ys, color=color, alpha=alpha, linewidth=0, zorder=zorder)

    def dot(self, x, y, r, color, hollow=False, ground=PAPER, stroke=3.0, alpha=1.0, zorder=7) -> None:
        if hollow:
            self.ax.add_patch(Circle((x, y), r - stroke / 2, facecolor=ground, edgecolor=color, linewidth=stroke,
                                     zorder=zorder))
        else:
            self.ax.add_patch(Circle((x, y), r, facecolor=color, edgecolor="none", alpha=alpha, zorder=zorder))

    def paragraph(self, x, y, width, markup, size, color=INK, leading=1.42, colors=None) -> float:
        """Wrap and draw ``markup`` with its first baseline at ``y``; returns the baseline after the last line."""
        words = parse_markup(markup)
        space = self.width_of("a a", size, "sans") - self.width_of("aa", size, "sans")

        def run_size(style):
            return size * (0.62 if style == "sup" else 1)

        widths = [sum(self.width_of(t, run_size(s), STYLE_ROLES[s]) for t, s in w) for w in words]
        for line in wrap_widths(widths, space, width):
            cursor = x
            for n, i in enumerate(line):
                for text, style in words[i]:
                    shift = -size * 0.36 if style == "sup" else 0
                    role = STYLE_ROLES[style]
                    self.text(cursor, y + shift, text, run_size(style), role, (colors or {}).get(style, color))
                    cursor += self.width_of(text, run_size(style), role)
                if n < len(line) - 1:
                    cursor += space
            y += size * leading
        return y

    def save(self, path: Path) -> None:
        self.fig.savefig(path, dpi=72, facecolor=self.fig.get_facecolor())
        plt.close(self.fig)


# Chart parts

def axis_frame(sheet: Sheet, x0, y0, x1, y1, xdom, ydom, xticks, yticks, xfmt, yfmt, xlabel=None) -> Frame:
    sx = linear(xdom[0], xdom[1], x0, x1)
    sy = linear(ydom[0], ydom[1], y1, y0)
    for t in yticks:
        y = float(sy(t))
        sheet.line([x0, x1], [y, y], RULE, 1.5, zorder=1)
        sheet.text(x0 - 16, y + 9, yfmt(t), TICK, "mono", INK_3, ha="right")
    sheet.line([x0, x1], [y1, y1], RULE_STRONG, 2, zorder=2)
    for t in xticks:
        x = float(sx(t))
        sheet.line([x, x], [y1, y1 + 10], RULE_STRONG, 2)
        sheet.text(x, y1 + 44, xfmt(t), TICK, "mono", INK_3, ha="center")
    if xlabel:
        sheet.text((x0 + x1) / 2, y1 + 86, xlabel, LABEL, "sans", INK_2, ha="center")
    return Frame(x0, y0, x1, y1, sx, sy)


def chart_title(sheet: Sheet, x0, x1, y, title, note=None) -> None:
    sheet.text(x0, y, title, LABEL, "sans_bold", INK)
    if note:
        sheet.text(x1, y, note, LABEL, "sans", INK_3, ha="right")


def caption(sheet: Sheet, x0, x1, y, key, title, body) -> float:
    return sheet.paragraph(x0, y, x1 - x0, f"**Figure {FIGURE_NUMBERS[key]}. {title}** {body}", CAPTION, INK_2,
                           leading=1.4, colors={"bold": INK})


def heading(sheet: Sheet, x0, y, text) -> float:
    sheet.text(x0 - 4, y, text, 62, "sans_bold", INK)
    return y + 66


def swatch(sheet: Sheet, x, y, color, label, kind="bar") -> float:
    """A legend key and its label; returns the x after it."""
    if kind == "bar":
        sheet.rect(x, y - 20, x + 34, y - 4, color, zorder=4)
    else:
        sheet.line([x, x + 34], [y - 12, y - 12], color, 5, cap="round")
    sheet.text(x + 48, y, label, TICK, "sans", INK_2)
    return x + 48 + sheet.width_of(label, TICK, "sans") + 40


# Figures

def figure_placement(sheet: Sheet, data: dict, x0, x1, y) -> float:
    h = ra.headline(data)
    p, e = data["placement"], data["economy"]["compartment_optimality"]
    rows = [("All positions shuffled", p["primary"]), ("Synapse-weighted cost", p["weighted"]),
            ("Within brain or cord", p["within_compartment"]), ("Synapse centroids", p["synapse_positions"]),
            ("Brain connections", e["brain"]), ("Nerve-cord connections", e["vnc"])]
    chart_title(sheet, x0, x1, y, "Wiring cost, relative to random placement", "1000 permutations each")
    px0, px1 = x0 + 370, x1 - 108
    sx = linear(0, 1.1, px0, px1)
    top, step = y + 86, 52
    bottom = top + step * (len(rows) - 1) + 32
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        sheet.line([float(sx(t))] * 2, [top - 32, bottom], RULE, 1.5, zorder=1)
        sheet.text(float(sx(t)), bottom + 40, f"{t:g}", TICK, "mono", INK_3, ha="center")
    sheet.line([px0, px1], [bottom, bottom], RULE_STRONG, 2)
    for i, (label, s) in enumerate(rows):
        yy = top + i * step
        sheet.text(x0, yy + 10, label, TICK, "sans_bold" if i == 0 else "sans", INK if i == 0 else INK_2)
        lo, hi = s["null_min"] / s["null_mean"], s["null_max"] / s["null_mean"]
        sheet.rect(float(sx(lo)) - 3, yy - 12, float(sx(hi)) + 3, yy + 12, NULL, alpha=0.85, zorder=3)
        sheet.dot(float(sx(s["cost_ratio"])), yy, 11, WIRE)
        sheet.text(x1, yy + 10, f"{s['cost_ratio']:.3f}", TICK, "mono_medium" if i == 0 else "mono",
                   INK if i == 0 else INK_2, ha="right")
    swap = float(sx(h["swap_ratio"]))
    sheet.line([swap + 12, float(sx(h["ratio"])) - 14], [top, top], WIRE, 3, dashes=(7, 6))
    sheet.dot(swap, top, 11, WIRE, hollow=True)
    sheet.text(swap, top - 24, f"after swaps {h['swap_ratio']:.3f}", 23, "mono_medium", WIRE_INK, ha="center")
    return caption(sheet, x0, x1, bottom + 104, "placement", "Less than half the cost of random, and far from optimal.",
                   f"Blue: the full range of the 1000 permutations; none came as low as the real layout. Hollow: the "
                   f"layout after 2,000,000 proposed swaps within compartments, which cut at least "
                   f"{ra.pct(h['swap'])} and had not converged.^2^")


def figure_distance(sheet: Sheet, data: dict, x0, x1, y) -> float:
    table = data["distance"]
    dependence = data["economy"]["distance_dependence"]
    minima = data["economy"]["probability_minima"]
    chart_title(sheet, x0, x1, y, "Share of cell-type pairs that connect", "20 µm bins")
    series = [("brain-brain", "brain", INK), ("vnc-vnc", "nerve cord", NULL), ("cross", "across the neck", WIRE)]
    x = x0
    for _, label, color in series:
        x = swatch(sheet, x, y + 52, color, label, "line")
    frame = axis_frame(sheet, x0 + 96, y + 88, x1, y + 330, (0, 1000), (-4.6, -1.5), [0, 250, 500, 750, 1000],
                       [-4, -3, -2], lambda t: f"{t:g}", lambda t: {-4: "0.01%", -3: "0.1%", -2: "1%"}[t],
                       xlabel="Distance between the two cell types (µm)")
    for key, _, color in series:
        kept = table[table[f"pairs_{key}"] >= 1000]
        centres = (kept["bin_start_um"] + 10).to_numpy()
        probability = (kept[f"edges_{key}"] / kept[f"pairs_{key}"]).to_numpy()
        keep = probability > 0
        sheet.line(frame.sx(centres[keep]), frame.sy(np.log10(probability[keep])), color, 3.6, zorder=5, cap="round")
    return caption(sheet, x0, x1, frame.y1 + 138, "distance", "Nearby cell types connect far more often.",
                   f"Length constant {dependence['all']['length_constant_um']:.0f} µm over all pairs. Within brain and "
                   f"cord it is lowest at {minima['brain-brain']['minimum_bin_um']:.0f} and "
                   f"{minima['vnc-vnc']['minimum_bin_um']:.0f} µm, then rises where connections join the two sides.")


def figure_cost(sheet: Sheet, data: dict, x0, x1, y) -> float:
    shares = data["economy"]["cost_share"]
    labels = {"neck-crossing": "Crossing the neck", "connective-incident": "Any descending or ascending edge",
              "high-degree-incident": f"Touching a hub (degree ≥ {shares['degree_threshold']:.0f})",
              "none of these": "None of these"}
    chart_title(sheet, x0, x1, y, "Share of connections and of wire", "mean length")
    sx = linear(0, 0.62, x0, x1 - 230)
    yy = y + 22
    for i, row in enumerate(shares["rows"]):
        yy += 48
        sheet.text(x0, yy, labels[row["label"]], TICK, "sans_bold" if i == 0 else "sans", INK if i == 0 else INK_2)
        sheet.text(x1, yy, f"{row['mean_length_um']:.0f} µm", TICK, "mono", INK_2, ha="right")
        for k, (share, color, ink) in enumerate(((row["edge_share"], RULE_STRONG, INK_3),
                                                 (row["cost_share"], WIRE, WIRE_INK))):
            top = yy + 14 + k * 24
            sheet.rect(x0, top, float(sx(share)), top + 18, color, zorder=3)
            sheet.text(float(sx(share)) + 12, top + 17, ra.pct(share), 23, "mono_medium" if k else "mono", ink)
        yy += 40
    x = swatch(sheet, x0, yy + 46, RULE_STRONG, "share of connections")
    swatch(sheet, x, yy + 46, WIRE, "share of wire")
    neck = shares["rows"][0]
    return caption(sheet, x0, x1, yy + 108, "cost", "The neck holds a quarter of the wire.",
                   f"Its {ra.count(neck['edges'])} connections average {neck['mean_length_um']:.0f} µm. Hub "
                   "connections are longer too, the high-cost backbone of the human connectome.^3^")


def figure_atlas(sheet: Sheet, data: dict, x0, x1, y) -> float:
    atlas = data["atlas"]
    totals = atlas["totals"]
    tested = [row for row in atlas["neuropils"] if "cost_ratio" in row]
    rows = atlas["neuropils"][:8]
    beyond = sum(1 for row in tested if row["n_at_or_below_real"] == 0)
    heaviest = atlas["pairs"][0]
    chart_title(sheet, x0, x1, y, "Wire held by each neuropil")
    x = swatch(sheet, x0, y + 50, WIRE, "brain")
    swatch(sheet, x, y + 50, NULL, "nerve cord")
    bx0, bx1 = x0 + 250, x0 + 545
    cx0, cx1 = x0 + 700, x1
    to_bar = linear(0, 0.105, bx0, bx1)
    to_ratio = linear(0.6, 1.05, cx0, cx1)
    sheet.text(bx0, y + 88, "share of all wire", 22, "sans", INK_3)
    sheet.text(cx0, y + 88, "internal wire, real over permuted", 22, "sans", INK_3)
    top, step = y + 126, 31
    bottom = top + step * (len(rows) - 1) + 22
    for t in (0, 0.05, 0.10):
        sheet.line([float(to_bar(t))] * 2, [top - 22, bottom], RULE, 1.5, zorder=1)
        sheet.text(float(to_bar(t)), bottom + 38, f"{100 * t:g}%", TICK, "mono", INK_3, ha="center")
    for t in (0.6, 0.8, 1.0):
        sheet.line([float(to_ratio(t))] * 2, [top - 22, bottom], RULE_STRONG if t == 1 else RULE,
                   2 if t == 1 else 1.5, zorder=1)
        sheet.text(float(to_ratio(t)), bottom + 38, f"{t:g}", TICK, "mono", INK_3, ha="center")
    for i, row in enumerate(rows):
        yy = top + i * step
        color = NULL if row["compartment"] == "vnc" else WIRE
        sheet.text(x0, yy + 8, row["neuropil"], 23, "mono_medium" if i == 0 else "mono",
                   INK if i == 0 else INK_2)
        sheet.rect(bx0, yy - 9, float(to_bar(row["wire_share"])), yy + 9, color, zorder=3)
        sheet.text(float(to_bar(row["wire_share"])) + 12, yy + 8, ra.pct(row["wire_share"]), 22, "mono", INK_3)
        spread = 1.96 * row["internal_null_sd_um"] / row["internal_null_mean_um"]
        sheet.rect(float(to_ratio(1 - spread)) - 3, yy - 8, float(to_ratio(1 + spread)) + 3, yy + 8, NULL, zorder=3)
        sheet.dot(float(to_ratio(row["cost_ratio"])), yy, 9, WIRE)
    return caption(sheet, x0, x1, bottom + 78, "atlas", "Every region large enough to test is packed cheaply.",
                   f"Each connection lends half its length to the neuropil nearest each end; only "
                   f"{ra.pct(totals['share_within_one_neuropil'])} of the wire stays inside one region, and "
                   f"{heaviest['a']}\u2013{heaviest['b']} carries the most between two, "
                   f"{ra.count(round(heaviest['wire_um'] / 1000))}\u00a0mm. Reshuffling a region's own types over "
                   f"its own positions puts all {len(tested)} below their permuted mean, {beyond} below every "
                   f"permutation.^2^")


def figure_concentration(sheet: Sheet, data: dict, x0, x1, y) -> float:
    result = data["concentration"]
    curves, lengths, tail = result["lorenz"], result["lengths"], result["tail"]
    whole = curves["all"]
    chart_title(sheet, x0, x1, y, "Wire against connections, longest first")
    px0, px1, py0, py1 = x0 + 96, x0 + 520, y + 62, y + 312
    frame = axis_frame(sheet, px0, py0, px1, py1, (0, 1), (0, 1), [0, 0.5, 1], [0, 0.5, 1],
                       lambda t: f"{100 * t:g}%", lambda t: f"{100 * t:g}%",
                       xlabel="Connections, longest first")
    sheet.line([px0, px1], [py1, py0], RULE_STRONG, 2, dashes=(7, 7), zorder=2)
    order = ["all", "within the brain", "within the nerve cord", "across the neck"]
    colors = {"all": WIRE, "within the brain": INK, "within the nerve cord": NULL, "across the neck": INK_3}
    for name in order:
        curve = curves[name]
        sheet.line(frame.sx(curve["connection_share"]), frame.sy(curve["wire_share"]), colors[name], 3.2, zorder=5)
    tenth = whole["top_shares"]["0.1"]
    sheet.dot(float(frame.sx(0.1)), float(frame.sy(tenth)), 10, WIRE)
    sheet.text(float(frame.sx(0.1)) + 24, float(frame.sy(tenth)) + 42, ra.pct(tenth), 24, "mono_medium", WIRE_INK)
    lx0 = x0 + 590
    sheet.text(lx0, y + 58, "Gini coefficient of length", 22, "sans", INK_3)
    for k, name in enumerate(order):
        yy = y + 96 + k * 37
        sheet.rect(lx0, yy - 20, lx0 + 30, yy - 6, colors[name], zorder=4)
        sheet.text(lx0 + 44, yy, ra.LORENZ_LABELS[name], 23, "sans", INK_2)
        sheet.text(x1, yy, f"{curves[name]['gini']:.3f}", 23, "mono", INK_2, ha="right")
    sheet.text(lx0, y + 266, "Share of the wire owned, and its mean length", 22, "sans", INK_3)
    for k, row in enumerate(result["superclasses"][:4]):
        yy = y + 302 + k * 34
        sheet.text(lx0, yy, ra.superclass_label(row["superclass"]), 23, "sans", INK_2)
        sheet.text(x1, yy, f"{ra.pct(row['wire_share'])}  {row['mean_length_um']:.0f}\u00a0µm", 23, "mono",
                   INK_2, ha="right")
    return caption(sheet, x0, x1, y + 442, "concentration",
                   "A tenth of the connections holds a third of the wire.",
                   f"Neck-crossing connections are the most uniform set of all, a median "
                   f"{lengths['across the neck']['median_um']:.0f}\u00a0µm against "
                   f"{lengths['within the brain']['median_um']:.0f}\u00a0µm inside the brain. A power law above "
                   f"{tail['xmin_um']:.0f}\u00a0µm has exponent {tail['alpha']:.2f} and beats an exponential, but "
                   f"a lognormal and a truncated power law fit the tail better.")


def figure_routes(sheet: Sheet, data: dict, x0, x1, y) -> float:
    rows = data["robustness"]["thresholds"]
    chart_title(sheet, x0, x1, y, "Rich-to-rich routes, real over rewired", "by edge threshold")
    frame = axis_frame(sheet, x0 + 86, y + 48, x1, y + 164, (0, len(rows)), (0.8, 1.8), [], [0.8, 1.0, 1.4, 1.8],
                       str, lambda t: f"{t:.1f}", xlabel="Edge threshold, share of the target's input")
    xs = [float(frame.sx(k + 0.5)) for k in range(len(rows))]
    lo, hi = [], []
    for r in rows:
        spread = 1.96 * r["routes"]["total"]["null_sd"] / r["routes"]["total"]["null_mean"]
        lo.append(float(frame.sy(1 - spread)))
        hi.append(float(frame.sy(1 + spread)))
    sheet.fill(xs + xs[::-1], hi + lo[::-1], NULL, alpha=0.22)
    sheet.line([frame.x0, frame.x1], [float(frame.sy(1))] * 2, RULE_STRONG, 2.5)
    ratios = [r["routes"]["total"]["ratio"] for r in rows]
    sheet.line(xs, [float(frame.sy(v)) for v in ratios], WIRE, 3.5)
    for x, r, v in zip(xs, rows, ratios):
        sheet.dot(x, float(frame.sy(v)), 12, WIRE, hollow=r["routes"]["total"]["p_value"] >= 0.05)
        sheet.text(x, float(frame.sy(v)) - 26, f"{v:.3f}", 23, "mono", INK_2, ha="center")
        sheet.text(x, frame.y1 + 40, f"{100 * r['fraction']:g}%", TICK, "mono", INK_3, ha="center")
    rc = data["richclub"]["routes_top10"]
    # The generative model has no panel of its own, so its one relevant success is given with its overall failure.
    properties = data["comparison"]["models"]["G"]["properties"]
    met = sum(1 for p in properties.values() if p["reproduced"])
    return caption(sheet, x0, x1, frame.y1 + 130, "routes", "The hub routing is modest and fragile.",
                   f"Routes from a rich partner on one side, through a connective type, to one on the other, "
                   f"against 1000 rewirings (blue: central 95%; filled: p{NBSP}<{NBSP}0.05). The "
                   f"{rc['total']['ratio']:.3f} excess at 1% vanishes at 0.5%, though connective types are "
                   "over-represented among hubs, as Lin et al. expected.^4^ Distance and cell class alone "
                   f"reproduce the count, but only {met} of {len(properties)} graph properties in all.")


def figure_value(sheet: Sheet, data: dict, x0, x1, y) -> float:
    value = data["value"]
    intact, real, families = value["intact"], value["real"], value["families"]["crossing_cost"]
    chart_title(sheet, x0, x1, y, "Sensory-to-motor flow lost", "share of intact")
    groups = [("flow", "All sensory to motor"), ("flow_brain_to_vnc", "Brain sensory to cord motor"),
              ("flow_vnc_to_brain", "Cord sensory to brain motor")]
    sx = linear(0, 0.7, x0, x1 - 175)
    yy = y + 22
    for i, (metric, label) in enumerate(groups):
        yy += 48
        sheet.text(x0, yy, label, TICK, "sans_bold" if i == 0 else "sans", INK if i == 0 else INK_2)
        sheet.text(x1, yy, f"{ra.count(intact[metric])} intact", 23, "mono", INK_3, ha="right")
        f = families[metric]
        bars = [(f["real"], WIRE, WIRE_INK), (f["null_mean"], NULL, NULL),
                (intact[metric] - real["longest"][metric], RULE_STRONG, INK_3)]
        for k, (lost, color, ink) in enumerate(bars):
            top = yy + 12 + k * 22
            share = lost / intact[metric]
            sheet.rect(x0, top, float(sx(share)), top + 17, color, zorder=3)
            sheet.text(float(sx(share)) + 12, top + 16, ra.count(lost), 23, "mono_medium" if k == 0 else "mono", ink)
        lo, hi = f["null_min"] / intact[metric], f["null_max"] / intact[metric]
        sheet.line([float(sx(lo)), float(sx(hi))], [yy + 42, yy + 42], INK, 2, zorder=4)
        yy += 72
    x = swatch(sheet, x0, yy + 38, WIRE, "neck cut")
    x = swatch(sheet, x, yy + 38, NULL, "random, same length")
    swatch(sheet, x, yy + 38, RULE_STRONG, "longest ordinary")
    flow = families["flow"]
    return caption(sheet, x0, x1, yy + 96, "value", "The neck buys less routing per unit of wire.",
                   f"Cutting it removes {flow['ratio']:.2f} times the flow of 1000 random sets of ordinary "
                   f"connections of the same length (black: their range), as much as the longest ordinary ones, and "
                   f"{families['flow_brain_to_vnc']['ratio']:.2f} times from brain to cord.")


def figure_price(sheet: Sheet, data: dict, x0, x1, y) -> float:
    nodes, tests = data["price_nodes"], data["price"]["tests"]
    chart_title(sheet, x0, x1, y, "Wire length and flow of each connective type")
    top = max(18, int(nodes["value"].max()) + 1)
    floor_mm = 0.5
    cells = split_cells(x0 + 56, x1, 2, 84)
    bottom = y + 292
    for (group, title), (cx0, cx1) in zip((("descending", "Descending"), ("ascending", "Ascending")), cells):
        part = nodes[nodes["direction"] == group]
        t = tests[group]
        first = cx0 == cells[0][0]
        sheet.text(cx0, y + 52, title, TICK, "sans_bold", INK)
        sheet.text(cx0, y + 86, f"ρ {ra.signed(t['spearman_rho'], 3)}, given edges "
                   f"{ra.signed(t['partial_rho'], 3)}", 23, "mono", INK_2)
        frame = axis_frame(sheet, cx0, y + 118, cx1, bottom, (math.log10(floor_mm), math.log10(200)), (0, top),
                           [0, 1, 2], [0, 5, 10, 15] if first else [], lambda v: f"{10 ** v:g} mm",
                           lambda v: f"{v:g}")
        if not first:
            for tick in (0, 5, 10, 15):
                sheet.line([frame.x0, frame.x1], [float(frame.sy(tick))] * 2, RULE, 1.5, zorder=1)
        xs = np.log10(np.maximum(part["price_um"].to_numpy() / 1000, floor_mm))
        values = part["value"].to_numpy()
        zero = values == 0
        for mask, color, r, alpha in ((zero, INK_3, 4, 0.35), (~zero, WIRE, 6, 0.6)):
            for x, v in zip(frame.sx(xs[mask]), frame.sy(values[mask])):
                sheet.dot(float(x), float(v), r, color, alpha=alpha, zorder=5)
    sheet.text((x0 + 56 + x1) / 2, bottom + 78, "Total length of the type's neck-crossing connections", LABEL,
               "sans", INK_2, ha="center")
    zero = (f"{tests['descending']['zero_value']} of {tests['descending']['n']} and "
            f"{tests['ascending']['zero_value']} of {ra.count(tests['ascending']['n'])}")
    return caption(sheet, x0, x1, bottom + 122, "price", "More wire does not buy a cell type more flow.",
                   "Each dot is a type on one side: the length of its neck-crossing connections and the flow lost "
                   f"when those alone are removed; {zero} lose none. At a given number of connections, longer "
                   "wiring buys nothing more.")


def figure_tradeoff(sheet: Sheet, data: dict, x0, x1, y) -> float:
    result = data["tradeoff"]
    curves, comparison = result["curves"], result["comparison"]
    reference = comparison["reference_wire_fraction"]
    at, per_metre = comparison["at_reference"], comparison["efficiency_lost_per_metre"]
    long_end, short_end = at["longest first"], at["shortest first"]
    chart_title(sheet, x0, x1, y, "Sensory-to-motor efficiency left", "share of the whole graph")
    x = x0
    for _, label, color, dashed in ra.TRADEOFF_SERIES:
        x = swatch(sheet, x, y + 52, {"wire": WIRE, "null": NULL, "ink3": INK_3}[color], label, "line")
    frame = axis_frame(sheet, x0 + 96, y + 84, x1, y + 300, (0, 0.6), (0, 1), [0, 0.2, 0.4, 0.6],
                       [0, 0.5, 1], lambda t: f"{100 * t:g}%", lambda t: f"{100 * t:g}%",
                       xlabel="Wire removed, share of the whole budget")
    for name, _, color, dashed in ra.TRADEOFF_SERIES:
        rows = curves[name]
        xs = [float(frame.sx(r["wire_removed_share"])) for r in rows]
        ys = [float(frame.sy(r["efficiency_share"])) for r in rows]
        artist = {"wire": WIRE, "null": NULL, "ink3": INK_3}[color]
        sheet.line(xs, ys, artist, 3.6, dashes=(8, 7) if dashed else None, zorder=5, cap="round")
    rx = float(frame.sx(reference))
    sheet.line([rx, rx], [frame.y0 - 14, frame.y1], RULE_STRONG, 2, dashes=(7, 7), zorder=2)
    for row, color, ink in ((long_end, WIRE, WIRE_INK), (short_end, NULL, NULL)):
        ry = float(frame.sy(row["efficiency_share"]))
        sheet.dot(rx, ry, 11, color)
        sheet.text(rx + 20, ry - 14, ra.pct(row["efficiency_share"]), 23, "mono_medium", ink)
    return caption(sheet, x0, x1, frame.y1 + 130, "tradeoff", "Short connections buy more per micrometre.",
                   f"At {ra.pct(reference, 0)} of the wire removed, taking it from the long end costs "
                   f"{ra.count(long_end['edges_removed'])} connections and leaves efficiency at "
                   f"{ra.pct(long_end['efficiency_share'])}; from the short end it costs "
                   f"{ra.count(short_end['edges_removed'])} and leaves {ra.pct(short_end['efficiency_share'])}, a "
                   f"factor of {per_metre['shortest first'] / per_metre['longest first']:.1f} per metre. "
                   "Exploratory, and run after the registered tests.")


FIGURE_DRAW = {"placement": figure_placement, "distance": figure_distance, "cost": figure_cost,
               "atlas": figure_atlas, "concentration": figure_concentration, "routes": figure_routes,
               "value": figure_value, "price": figure_price, "tradeoff": figure_tradeoff}


# Sections

def draw_front(sheet: Sheet, front: dict, x0, y0, size, width: float = 1.1, alpha: float = 0.5) -> None:
    """The CNS silhouette and the sampled neck-crossing wires, shortest first, fitted into a square box.

    Parameters: ``width`` and ``alpha`` set the wire stroke, which a smaller box needs lighter.
    """
    lo, hi = np.array(front["bounds"]["min"]), np.array(front["bounds"]["max"])
    scale = size / float((hi - lo).max())
    ox = x0 + (size - (hi[0] - lo[0]) * scale) / 2
    oy = y0 + (size - (hi[1] - lo[1]) * scale) / 2
    for outline in front["outlines"]:
        points = np.array(outline)
        xs, ys = ox + (points[:, 0] - lo[0]) * scale, oy + (hi[1] - points[:, 1]) * scale
        sheet.fill(xs, ys, FIELD_TISSUE, zorder=1)
        sheet.line(np.r_[xs, xs[:1]], np.r_[ys, ys[:1]], FIELD_EDGE, 2, zorder=2)
    wires = np.array(front["wires"])
    a, b = front["length_range_um"]
    starts = np.column_stack([ox + (wires[:, 0] - lo[0]) * scale, oy + (hi[1] - wires[:, 1]) * scale])
    ends = np.column_stack([ox + (wires[:, 2] - lo[0]) * scale, oy + (hi[1] - wires[:, 3]) * scale])
    colors = [ra.ramp_color(DARK["ramp"], (length - a) / (b - a)) for length in wires[:, 4]]
    sheet.ax.add_collection(LineCollection(np.stack([starts, ends], axis=1), colors=colors, linewidths=width,
                                           alpha=alpha, zorder=3, capstyle="round"))


def draw_band(sheet: Sheet, data: dict, edges) -> None:
    h = ra.headline(data)
    front = data["front"]
    sheet.rect(0, 0, WIDTH, BAND_HEIGHT, FIELD, zorder=0)
    x0 = MARGIN
    text_right = edges[0][1] + 260
    sheet.text(x0 - 10, 300, "The Price", 220, "sans_bold", FIELD_INK)
    sheet.text(x0 - 10, 530, "of Thought", 220, "sans_bold", FIELD_INK)
    sheet.paragraph(x0, 660, text_right - x0, "Is a fly's nervous system wired to keep its connections short, and "
                    "what do its longest wires buy?", 54, FIELD_INK, leading=1.26)

    sheet.line([x0, text_right], [860, 860], FIELD_RULE, 2)
    cells = split_cells(x0, text_right, 2, 70)
    sheet.text(cells[0][0] - 6, 1000, f"{h['ratio']:.3f}×", 140, "mono_medium", WIRE_GLOW)
    sheet.text(cells[1][0] - 6, 1000, ra.pct(h["neck_cost_share"]), 140, "mono_medium", FIELD_INK_2)
    sheet.paragraph(cells[0][0], 1052, cells[0][1] - cells[0][0], "the wiring cost of the real placement of cell "
                    "types, against random placements", 29, FIELD_INK, leading=1.36)
    sheet.paragraph(cells[1][0], 1052, cells[1][1] - cells[1][0], f"of all wire, in the {ra.pct(h['neck_edge_share'])} "
                    "of connections that cross the neck", 29, FIELD_INK_2, leading=1.36)

    sheet.line([x0, WIDTH - MARGIN], [1140, 1140], FIELD_RULE, 2)
    sheet.text(x0, 1212, AUTHOR, 38, "sans_bold", FIELD_INK)
    sheet.paragraph(x0 + sheet.width_of(AUTHOR, 38, "sans_bold") + 44, 1212, 2200,
                    "Complete male adult *Drosophila* CNS connectome, neuPrint male-cns:v1.0. Independent, "
                    "pre-registered analysis, not peer reviewed.", 29, FIELD_INK_2)
    sheet.text(WIDTH - MARGIN, 1212, REPO_URL.removeprefix("https://"), 29, "sans_medium", FIELD_INK, ha="right")

    draw_front(sheet, front, text_right + 60, 40, 1080)

    lx0, lx1 = text_right + 1200, WIDTH - MARGIN
    y = sheet.paragraph(lx0, 620, lx1 - lx0, "The male CNS seen from the front, brain above and nerve cord below.",
                        29, FIELD_INK_2, leading=1.36) + 20
    y = sheet.paragraph(lx0, y, lx1 - lx0, f"**{ra.count(front['sample']['n'])} of the "
                        f"{ra.count(front['crossing_edges'])} neck-crossing connections,** a fixed random sample, "
                        "drawn straight between cell-type positions and coloured by length.", 29, FIELD_INK_2,
                        leading=1.36, colors={"bold": FIELD_INK}) + 30
    a, b = front["length_range_um"]
    ramp = np.array([[to_rgb(ra.ramp_color(DARK["ramp"], t)) for t in np.linspace(0, 1, 256)]])
    sheet.ax.imshow(ramp, extent=(lx0, lx1, y + 24, y), aspect="auto", zorder=4, interpolation="bilinear")
    sx = linear(a, b, lx0, lx1)
    for t in np.arange(a, b + 1, 200):
        sheet.text(float(sx(t)), y + 66, f"{t:g}", 25, "mono", FIELD_INK_2, ha="center")
    sheet.text(lx0, y + 112, "connection length (µm)", 25, "sans", FIELD_INK_2)


def draw_methods(sheet: Sheet, data: dict) -> None:
    h = ra.headline(data)
    y = BAND_HEIGHT
    steps = [
        ("Data", f"neuPrint male-cns:v1.0, {ra.count(ra.TYPED_NEURONS)} typed neurons, chemical synapses"),
        ("Graph", f"{ra.count(h['nodes'])} cell types by side at their soma centroids, {ra.count(h['edges'])} "
                  "connections"),
        ("Pre-register", f"every hypothesis committed before it was computed, in {len(ra.PREREGISTRATION_COMMITS)} "
                         "commits"),
        ("Placement", "1000 permutations of positions; 2,000,000 proposed swaps; 1000 more inside each "
                      "neuropil"),
        ("Connective", "1000 layer-preserving rewirings; 1000 length-matched removals"),
        ("Model", "logistic fit on distance, compartment and class; 50 synthetic graphs"),
    ]
    sheet.rect(0, y, WIDTH, y + METHODS_HEIGHT, WASH, zorder=0)
    for i, ((label, body), (cx0, cx1)) in enumerate(zip(steps, split_cells(MARGIN, WIDTH - MARGIN, 6, 56))):
        sheet.text(cx0, y + 96, str(i + 1), 56, "mono_medium", WIRE_INK)
        sheet.text(cx0 + 52, y + 88, label, 31, "sans_bold", INK)
        sheet.paragraph(cx0 + 52, y + 134, cx1 - cx0 - 52, body, 27, INK_2, leading=1.36)


def draw_lede(sheet: Sheet, data: dict, edges) -> float:
    """The question on the left and the headline findings across the other two columns."""
    sheet.line([MARGIN, WIDTH - MARGIN], [LEDE_TOP - 36, LEDE_TOP - 36], INK, 3)
    x0, x1 = edges[0]
    y = heading(sheet, x0, LEDE_TOP + 40, "Question")
    bottom = sheet.paragraph(x0, y + 6, x1 - x0, QUESTION, 31, INK, leading=1.4, colors={"bold": INK})
    cells = split_cells(edges[1][0], edges[2][1], 3, GUTTER)
    for (label, value, body, color), (cx0, cx1) in zip(lede_findings(data), cells):
        sheet.text(cx0, LEDE_TOP + 24, label, 29, "sans_bold", INK)
        sheet.text(cx0 - 6, LEDE_TOP + 146, value, 110, "mono_medium", color)
        bottom = max(bottom, sheet.paragraph(cx0, LEDE_TOP + 202, cx1 - cx0, body, 27, INK_2, leading=1.38))
    return bottom


def draw_figure_column(sheet: Sheet, data: dict, x0, x1, y, keys: tuple[str, ...]) -> float:
    """One column of figures, each preceded by its section heading when it opens one."""
    for i, key in enumerate(keys):
        if key in COLUMN_HEADINGS:
            y = heading(sheet, x0, y + (0 if i == 0 else 34), COLUMN_HEADINGS[key]) + 22
        else:
            y += 46
        y = FIGURE_DRAW[key](sheet, data, x0, x1, y)
    return y


def draw_checks(sheet: Sheet, data: dict) -> float:
    """The pre-registered register across two columns, with the limitations beside it in the third."""
    y = CHECKS_TOP
    sheet.line([MARGIN, WIDTH - MARGIN], [y, y], INK, 3)
    edges = column_edges(WIDTH, MARGIN, GUTTER, COLUMNS)
    items = hypotheses(data)
    supported = sum(ok for _, _, ok in items)
    sheet.text(MARGIN, y + 78, "Pre-registered hypotheses", 54, "sans_bold", INK)
    sheet.text(edges[1][1], y + 78, f"{supported} of {len(items)} supported", CAPTION, "sans", INK_3, ha="right")
    per = math.ceil(len(items) / 2)
    ends = []
    for c, (cx0, cx1) in enumerate(edges[:2]):
        yy = y + 138
        for label, text, ok in items[c * per:(c + 1) * per]:
            sheet.dot(cx0 + 11, yy - 9, 11, INK if ok else WIRE, hollow=not ok)
            sheet.text(cx0 + 36, yy, label, 25, "mono_medium", INK)
            yy = sheet.paragraph(cx0 + 120, yy, cx1 - cx0 - 120, text, 25, INK_2 if ok else WIRE_INK,
                                 leading=1.34) + 12
        ends.append(yy)
    base = max(ends) + 18
    sheet.dot(MARGIN + 11, base - 9, 11, INK)
    sheet.text(MARGIN + 36, base, "supported", 24, "sans", INK_3)
    x = MARGIN + 36 + sheet.width_of("supported", 24, "sans") + 40
    sheet.dot(x + 11, base - 9, 11, WIRE, hollow=True)
    sheet.text(x + 36, base, "not supported. Each was committed, with its direction and null, before it was "
                             f"computed: {', '.join(ra.PREREGISTRATION_COMMITS)}.", 24, "sans", INK_3)

    lx0, lx1 = edges[2]
    sheet.text(lx0, y + 78, "Where it falls short", 54, "sans_bold", INK)
    yy = y + 138
    for lead, text in limitations(data):
        yy = sheet.paragraph(lx0, yy, lx1 - lx0, f"**{lead}** {text}", 25, INK_2, leading=1.32,
                             colors={"bold": INK}) + 7
    return max(base, yy)


def draw_footer(sheet: Sheet) -> None:
    y = FOOTER_TOP
    sheet.line([MARGIN, WIDTH - MARGIN], [y, y], RULE_STRONG, 2)
    modules = encode(REPO_URL, "M")
    size = 290
    cell = size / len(modules)
    qy = y + 60
    verts, codes = [], []
    for r, c in zip(*np.nonzero(modules)):
        bx, by = MARGIN + c * cell, qy + r * cell
        verts += [(bx, by), (bx + cell, by), (bx + cell, by + cell), (bx, by + cell), (bx, by)]
        codes += [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO, MplPath.LINETO, MplPath.CLOSEPOLY]
    sheet.ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=INK, edgecolor="none", zorder=6,
                                 antialiased=False))

    cols = split_cells(MARGIN + size + 60, WIDTH - MARGIN, 4, 70)
    x0, x1 = cols[0]
    sheet.text(x0, qy + 30, "Code, results and technical report", CAPTION, "sans_bold", INK)
    sheet.text(x0, qy + 72, REPO_URL.removeprefix("https://"), CAPTION, "sans_bold", WIRE_INK)
    yy = sheet.paragraph(x0, qy + 122, x1 - x0, "make reproduce rebuilds every number from neuPrint; make verify "
                         "re-reduces the saved draws and checks every committed result.", 27, INK_2,
                         leading=1.38)
    sheet.paragraph(x0, yy + 8, x1 - x0, "Data: HHMI Janelia FlyEM and Google Research, CC-BY 4.0. Code: MIT.", 25,
                    INK_3, leading=1.38)

    x0, x1 = cols[1]
    sheet.text(x0, qy + 30, "Cite as", CAPTION, "sans_bold", INK)
    yy = sheet.paragraph(x0, qy + 76, x1 - x0, "Sarkar D (2026). The Price of Thought: wiring cost and the "
                         "brain-nerve cord connective in the complete *Drosophila* male CNS connectome. "
                         f"{REPO_URL.removeprefix('https://')}", 27, INK_2, leading=1.38)
    sheet.paragraph(x0, yy + 8, x1 - x0, "Third of three studies of this connectome, after ConnectomeLens and "
                    "Fault Lines.", 25, INK_3, leading=1.38)
    for (x0, x1), group, start in zip(cols[2:], (REFERENCES[:2], REFERENCES[2:]), (1, 3)):
        yy = qy + 30
        for n, ref in enumerate(group, start=start):
            sheet.text(x0, yy, str(n), 25, "sans_bold", INK_3)
            yy = sheet.paragraph(x0 + 34, yy, x1 - x0 - 34, ref, 25, INK_2, leading=1.38) + 12


def load_results() -> dict:
    """Every result the poster draws on: the README inputs plus the cable-length check."""
    data = ra.load_inputs()
    data["cable"] = json.loads((RESULTS / "cable_length.json").read_text(encoding="utf-8"))
    return data


def render(output: Path = POSTER_PATH, preview: Path = PREVIEW_PATH) -> dict[str, float]:
    """Draw the poster and its preview; returns the bottom of each column and section, for layout checks."""
    reading_order()
    load_fonts()
    data = load_results()
    sheet = Sheet(WIDTH, HEIGHT)
    edges = column_edges(WIDTH, MARGIN, GUTTER, COLUMNS)
    draw_band(sheet, data, edges)
    draw_methods(sheet, data)
    bottoms = {"lede": draw_lede(sheet, data, edges)}
    for i, keys in enumerate(FIGURE_LAYOUT):
        bottoms[f"column {i + 1}"] = draw_figure_column(sheet, data, *edges[i], COLUMN_TOP, keys)
    bottoms["checks"] = draw_checks(sheet, data)
    draw_footer(sheet)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    with Image.open(output) as im:
        im = im.convert("RGB")
        im.save(output, dpi=(PRINT_DPI, PRINT_DPI), optimize=True)
        height = round(PREVIEW_WIDTH * im.height / im.width)
        im.resize((PREVIEW_WIDTH, height), Image.Resampling.LANCZOS).save(preview, optimize=True)
    return bottoms


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=POSTER_PATH)
    parser.add_argument("--preview", type=Path, default=PREVIEW_PATH)
    args = parser.parse_args()
    bottoms = render(args.output, args.preview)
    print("Bottoms: " + ", ".join(f"{k} {v:.0f}" for k, v in bottoms.items())
          + f" (columns start {COLUMN_TOP}, checks {CHECKS_TOP}, footer {FOOTER_TOP})")
    print(f"Wrote {args.output} ({WIDTH} x {HEIGHT}) and {args.preview}")


if __name__ == "__main__":
    main()
