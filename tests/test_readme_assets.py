import xml.etree.ElementTree as ET

import numpy as np
import pytest

from pipeline import readme_assets as ra


def test_linear_maps_endpoints_and_midpoint():
    to_x = ra.linear(0, 0.5, 100, 200)
    assert to_x(0) == 100
    assert to_x(0.5) == 200
    assert to_x(0.25) == 150


def test_linear_can_invert_an_axis():
    to_y = ra.linear(0, 1, 800, 200)
    assert to_y(1) == 200
    assert to_y(0.5) == 500


@pytest.mark.parametrize(
    ("value", "digits", "expected"),
    [(0.0753, 1, "7.5%"), (0.24, 1, "24.0%"), (0.336, 1, "33.6%"), (0.5, 0, "50%"), (0.0, 1, "0.0%")],
)
def test_pct(value, digits, expected):
    assert ra.pct(value, digits) == expected


def test_count_and_signed():
    assert ra.count(490884) == "490,884"
    assert ra.count(36943.4) == "36,943"
    assert ra.signed(-0.1224, 3) == "−0.122"
    assert ra.signed(0.231, 3) == "0.231"


@pytest.mark.parametrize(("value", "expected"), [(12.0, "12"), (12.34, "12.3"), (-0.01, "0"), (0.05, "0.1")])
def test_num_drops_trailing_zeros(value, expected):
    assert ra.num(value) == expected


def test_text_width_grows_with_length_size_and_weight():
    base = ra.text_width("Wiring cost", 26)
    assert ra.text_width("Wiring cost relative", 26) > base
    assert ra.text_width("Wiring cost", 52) == pytest.approx(2 * base)
    assert ra.text_width("Wiring cost", 26, weight=600) > base


def test_wrap_keeps_every_word_and_respects_width():
    text = "Real routes divided by the mean of 1000 layer-preserving rewirings of the connective"
    lines = ra.wrap(text, 26, 300)
    assert " ".join(lines) == text
    assert len(lines) > 1
    assert all(ra.text_width(line, 26) <= 300 or " " not in line for line in lines)


def test_wrap_returns_single_line_when_it_fits():
    assert ra.wrap("short line", 26, 1000) == ["short line"]


def test_spread_separates_close_labels_and_keeps_order():
    placed = ra.spread([100, 105, 110, 400], 30)
    ordered = sorted(placed)
    assert all(b - a >= 30 - 1e-6 for a, b in zip(ordered, ordered[1:]))
    assert placed[0] < placed[1] < placed[2] < placed[3]
    assert placed[3] == 400


def test_spread_respects_bounds():
    placed = ra.spread([0, 1, 2], 20, lo=10, hi=100)
    assert min(placed) >= 10 - 1e-6
    assert max(placed) <= 100 + 1e-6


def test_spread_leaves_distant_labels_alone():
    assert ra.spread([10, 200, 500], 30) == [10, 200, 500]


def test_ramp_color_endpoints_and_midpoint():
    stops = ("#000000", "#ffffff")
    assert ra.ramp_color(stops, 0) == "#000000"
    assert ra.ramp_color(stops, 1) == "#ffffff"
    assert ra.ramp_color(stops, 0.5) == "#808080"
    assert ra.ramp_color(stops, 2) == "#ffffff"


def test_ramp_color_walks_multiple_stops():
    stops = ("#000000", "#ff0000", "#ffffff")
    assert ra.ramp_color(stops, 0.5) == "#ff0000"
    assert ra.ramp_color(stops, 0.75) == "#ff8080"


def test_histogram_outline_is_a_closed_step_with_unit_peak():
    xs, ys = ra.histogram_outline(np.array([0.5, 1.5, 1.6, 2.5]), np.array([0.0, 1.0, 2.0, 3.0]))
    assert xs[0] == 0 and ys[0] == 0
    assert xs[-1] == 3 and ys[-1] == 0
    assert max(ys) == 1
    assert 0.5 in ys


def test_svg_render_is_well_formed_and_accessible():
    svg = ra.Svg(200, "dark")
    svg.text(10, 20, "Cost & value < 50%")
    svg.line(0, 0, 10, 10, "wire", dash="4 4")
    svg.polyline([0, 5, 10], [0, 5, 0], "null")
    svg.dot(5, 5, 4, "wire", hollow=True, ring=2)
    document = svg.render("Cost & value", "A description < 50%")
    root = ET.fromstring(document)
    assert root.get("viewBox") == f"0 0 {ra.WIDTH} 200"
    assert root.get("role") == "img"
    ns = "{http://www.w3.org/2000/svg}"
    assert root.find(f"{ns}title").text == "Cost & value"
    assert root.find(f"{ns}desc").text == "A description < 50%"
    assert ra.THEMES["dark"]["wire"] in document


def test_text_is_set_as_outlines_with_each_glyph_defined_once():
    svg = ra.Svg(100, "light")
    svg.text(10, 50, "connective")
    document = svg.render("t", "d")
    assert "<text" not in document
    ids = [p.get("id") for p in ET.fromstring(document).iter("{http://www.w3.org/2000/svg}path") if p.get("id")]
    assert len(ids) == len(set(ids)) == len(set("connective"))
    assert document.count("<use ") == len("connective")


def test_text_anchor_offsets_by_the_measured_width():
    svg = ra.Svg(100, "light")
    width = svg.text(500, 50, "Mean length", 26, anchor="end")
    assert width == pytest.approx(ra.text_width("Mean length", 26))
    origin = float(svg.parts[-1].split("matrix(")[1].split()[4])
    assert origin == pytest.approx(500 - width, abs=0.06)


def test_theme_tokens_resolve_per_theme():
    assert ra.Svg(10, "light").c("wire") == ra.THEMES["light"]["wire"]
    assert ra.Svg(10, "dark").c("wire") == ra.THEMES["dark"]["wire"]
    assert ra.Svg(10, "light").c("#123456") == "#123456"


def test_every_asset_builds_from_the_committed_results(tmp_path):
    written = ra.build_all(ra.load_inputs(), tmp_path)
    names = {p.name for p in written}
    assert "plate-title.svg" in names
    for stem in ("stat-plate", "fig-placement", "fig-distance", "fig-cost", "fig-routes", "fig-value", "fig-price",
                 "fig-generative", "methods-pipeline"):
        assert {f"{stem}-light.svg", f"{stem}-dark.svg"} <= names
    for path in written:
        text = path.read_text(encoding="utf-8")
        ET.fromstring(text)
        for forbidden in (chr(0x2014), chr(0x2013), chr(0x00B7)):
            assert forbidden not in text, (path.name, forbidden)
        assert "<text" not in text
        assert "<use " in text
        assert path.stat().st_size < 300_000, path.name


def test_build_is_deterministic(tmp_path):
    data = ra.load_inputs()
    first = {p.name: p.read_bytes() for p in ra.build_all(data, tmp_path / "a")}
    second = {p.name: p.read_bytes() for p in ra.build_all(data, tmp_path / "b")}
    assert first == second


def test_headline_numbers_come_from_the_results():
    h = ra.headline(ra.load_inputs())
    assert h["nodes"] == 23073
    assert h["edges"] == 490884
    assert h["neck_edges"] == 36943
    assert f"{h['ratio']:.3f}" == "0.459"
    assert f"{h['within']:.3f}" == "0.728"
    assert ra.pct(h["swap"]) == "33.6%"
    assert ra.pct(h["neck_edge_share"]) == "7.5%"
    assert ra.pct(h["neck_cost_share"]) == "24.0%"
    assert f"{h['routes']:.3f}" == "1.103"
    assert f"{h['value_ratio']:.2f}" == "0.36"
    assert f"{h['value_b2v']:.2f}" == "1.83"
