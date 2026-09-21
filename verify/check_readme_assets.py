"""Check every README figure is committed, well formed, and is exactly what the current results draw."""

import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline import fonts, readme_assets as ra
from verify.common import Skip, run

NS = "{http://www.w3.org/2000/svg}"


def well_formed(path: Path) -> None:
    """A committed figure parses, carries a description, sets its text as outlines and defines every glyph."""
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    desc = root.find(f"{NS}desc")
    assert desc is not None and desc.text, f"{path.name} carries no description"
    assert root.find(f".//{NS}text") is None, f"{path.name} sets text as characters rather than outlines"
    defined = {p.get("id") for p in root.iter(f"{NS}path") if p.get("id")}
    placed = {u.get("href", "")[1:] for u in root.iter(f"{NS}use")}
    assert placed, f"{path.name} places no glyph"
    assert placed <= defined, f"{path.name} places glyphs it never defines: {sorted(placed - defined)}"


def check() -> str:
    committed = sorted(ra.OUT_DIR.glob("*.svg"))
    assert committed, f"{ra.OUT_DIR} holds no figure; run make readme"
    for path in committed:
        well_formed(path)

    data = ra.load_inputs()
    try:
        jobs = [ra.title_plate(data)] + [build(data, theme) for build in ra.THEMED for theme in ra.THEMES]
    except fonts.FontsUnavailable as error:
        raise Skip(f"{len(committed)} committed figures are well formed but none could be redrawn: {error}") from error

    drawn = {name: (svg, desc) for svg, desc, name in jobs}
    difference = set(drawn) ^ {path.name for path in committed}
    assert not difference, f"the figures drawn and the ones committed differ: {', '.join(sorted(difference))}"

    described = [name for name, (_, desc) in drawn.items()
                 if ET.fromstring((ra.OUT_DIR / name).read_text(encoding="utf-8")).find(f"{NS}desc").text != desc]
    assert not described, \
        f"{len(described)} figures describe other numbers than the results: {', '.join(sorted(described))}"
    # The same description over a different drawing means the drawing code or the typefaces have moved,
    # which changes glyph widths without changing a single number.
    stale = [name for name, (svg, _) in drawn.items() if (ra.OUT_DIR / name).read_text(encoding="utf-8") != svg]
    assert not stale, (f"{len(stale)} figures state the right numbers but are not drawn as the code draws them: "
                       f"{', '.join(sorted(stale))}; run make readme. Typefaces in use: "
                       f"{', '.join(p.name for p in fonts.cached_fonts())}")
    return f"{len(jobs)} README figures redraw from the results byte for byte, glyph outlines included"


if __name__ == "__main__":
    run(check)
