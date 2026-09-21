"""Draw the social preview card: the title plate's artwork at the size link previews are served at."""

import argparse
from pathlib import Path

import numpy as np
from matplotlib.colors import to_rgb
from PIL import Image

from pipeline import poster
from pipeline import readme_assets as ra
from pipeline.common import ASSETS

WIDTH, HEIGHT = 1280, 640
MARGIN = 52
COLUMN = 582
CARD_PATH = ASSETS / "social-preview.png"


def draw(sheet: poster.Sheet, data: dict) -> None:
    """The name, the question, the two budget shares and the front view, on the black field."""
    h = ra.headline(data)
    front = data["front"]
    wire_mm = data["concentration"]["total_wire_um"] / 1000
    right = WIDTH - MARGIN

    sheet.rect(0, 0, WIDTH, HEIGHT, poster.FIELD, zorder=0)
    sheet.text(MARGIN - 4, 122, "The Price", 93, "sans_bold", poster.FIELD_INK)
    sheet.text(MARGIN - 4, 215, "of Thought", 93, "sans_bold", poster.FIELD_INK)
    sheet.paragraph(MARGIN, 268, COLUMN, "Is a fly's nervous system wired to keep its connections short, and what "
                    "do its longest wires buy?", 27, poster.FIELD_INK, leading=1.26)

    sheet.line([MARGIN, MARGIN + COLUMN], [370, 370], poster.FIELD_RULE, 2)
    runs = [(f"{ra.count(h['nodes'])} cell types sit where they cost ", "sans"), (f"{h['ratio']:.3f}", "sans_bold"),
            (" times random placement.", "sans")]
    x = MARGIN
    for text, role in runs:
        sheet.text(x, 404, text, 20, role, poster.FIELD_INK)
        x += sheet.width_of(text, 20, role)

    # Both shares run on one track length, so the wire bar can be read against the connection bar above it.
    rows = [(h["neck_edge_share"], f"of {ra.count(h['edges'])} connections cross the neck"),
            (h["neck_cost_share"], f"of {ra.count(wire_mm)} mm of wire runs through it")]
    gutter = max(sheet.width_of(ra.pct(share), 38, "sans_bold") for share, _ in rows) + 24
    for i, (share, label) in enumerate(rows):
        y = 460 + i * 66
        sheet.text(MARGIN, y, ra.pct(share), 38, "sans_bold", poster.FIELD_INK)
        sheet.text(MARGIN + gutter, y - 1, label, 20, "sans", poster.FIELD_INK_2)
        sheet.rect(MARGIN, y + 13, MARGIN + COLUMN, y + 20, poster.FIELD_RULE)
        sheet.rect(MARGIN, y + 13, MARGIN + COLUMN * share, y + 20, poster.WIRE_GLOW)

    sheet.line([MARGIN, right], [572, 572], poster.FIELD_RULE, 2)
    sheet.text(MARGIN, 599, poster.AUTHOR, 20, "sans_bold", poster.FIELD_INK)
    sheet.text(MARGIN, 626, "Adult male Drosophila CNS connectome, male-cns:v1.0", 17, "sans", poster.FIELD_INK_2)
    sheet.text(right, 599, f"{ra.count(front['sample']['n'])} of the {ra.count(front['crossing_edges'])} "
               "connections that cross the neck", 17, "sans", poster.FIELD_INK_2, ha="right")
    length_legend(sheet, front["length_range_um"], right - 300, right, 626)

    poster.draw_front(sheet, front, 712, 22, 516, width=0.8, alpha=0.32)


def length_legend(sheet: poster.Sheet, length_range, x0: float, x1: float, y: float) -> None:
    """The length ramp with its end values, as the wires in the front view are coloured."""
    low, high = length_range
    ramp = np.array([[to_rgb(ra.ramp_color(poster.DARK["ramp"], t)) for t in np.linspace(0, 1, 256)]])
    bar0, bar1 = x0 + sheet.width_of(f"{low:,.0f}", 17, "mono") + 14, x1 - sheet.width_of("1,000 µm", 17, "mono") - 14
    sheet.ax.imshow(ramp, extent=(bar0, bar1, y - 4, y - 14), aspect="auto", zorder=4, interpolation="bilinear")
    sheet.text(x0, y, f"{low:,.0f}", 17, "mono", poster.FIELD_INK_2)
    sheet.text(bar1 + 14, y, f"{high:,.0f} µm", 17, "mono", poster.FIELD_INK_2)


def render(output: Path = CARD_PATH) -> tuple[int, int]:
    """Draw the card and write it as an optimized PNG; returns its pixel size."""
    poster.load_fonts()
    sheet = poster.Sheet(WIDTH, HEIGHT, ground=poster.FIELD)
    draw(sheet, ra.load_inputs())
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    with Image.open(output) as image:
        image.convert("RGB").save(output, optimize=True)
        return image.size


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=CARD_PATH)
    args = parser.parse_args()
    size = render(args.output)
    print(f"Wrote {args.output} ({size[0]} x {size[1]})")


if __name__ == "__main__":
    main()
