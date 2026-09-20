import re

import numpy as np
import pytest
from PIL import Image

from pipeline import poster
from pipeline.common import RESULTS
from pipeline.poster import (
    NBSP,
    REFERENCES,
    column_edges,
    hypotheses,
    linear,
    load_results,
    parse_markup,
    reading_order,
    split_cells,
    wrap_widths,
)


def test_columns_fill_the_width_between_margins_with_equal_gutters():
    edges = column_edges(3508, 128, 88, 3)
    assert edges[0][0] == pytest.approx(128)
    assert edges[-1][1] == pytest.approx(3508 - 128)
    widths = [right - left for left, right in edges]
    assert widths == pytest.approx([widths[0]] * 3)
    assert edges[1][0] - edges[0][1] == pytest.approx(88)


def test_split_cells_divides_a_span_into_equal_cells():
    cells = split_cells(100, 700, 3, 30)
    assert cells[0] == pytest.approx((100, 280))
    assert cells[1] == pytest.approx((310, 490))
    assert cells[2] == pytest.approx((520, 700))


def test_linear_scale_maps_endpoints_and_can_invert_direction():
    sy = linear(0, 1, 500, 100)
    assert sy(0) == pytest.approx(500)
    assert sy(1) == pytest.approx(100)
    assert np.allclose(linear(0, 10, 0, 100)([0, 5, 10]), [0, 50, 100])


def test_figures_are_numbered_as_in_the_readme_and_read_in_order():
    assert reading_order() == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    with pytest.raises(ValueError):
        reading_order((("b",), ("a",)), {"a": 1, "b": 2})


def test_wrap_breaks_greedily_and_never_leaves_an_empty_line():
    assert wrap_widths([40, 40, 40], 10, 95) == [[0, 1], [2]]
    assert wrap_widths([200, 10], 10, 100) == [[0], [1]]
    assert wrap_widths([], 10, 100) == []


def test_markup_toggles_styles_and_attaches_superscripts():
    words = parse_markup("**Figure 1.** the *Drosophila* CNS,^1^ p = 0.05")
    assert words[0] == [("Figure", "bold")]
    assert words[1] == [("1.", "bold")]
    assert words[3] == [("Drosophila", "italic")]
    assert words[4] == [("CNS,", "regular"), ("1", "sup")]
    assert parse_markup(f"p{NBSP}={NBSP}0.05") == [[(f"p{NBSP}={NBSP}0.05", "regular")]]


def test_hypotheses_follow_the_result_files():
    items = hypotheses(load_results())
    labels = [label for label, _, _ in items]
    assert labels == ["H", "H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9", "H10", "H10b", "H11"]
    outcome = {label: ok for label, _, ok in items}
    assert [label for label, ok in outcome.items() if not ok] == ["H4", "H10", "H10b", "H11"]
    registered = (RESULTS / "preregistration.md").read_text(encoding="utf-8")
    for label, ok in outcome.items():
        row = re.search(rf"^\| {label} \|.*\| (\S.*?) \|$", registered, re.M).group(1)
        assert ("not supported" not in row) == ok, label


def test_every_reference_is_one_verified_in_the_prior_art_review():
    reviewed = (RESULTS / "prior_art.md").read_text(encoding="utf-8").partition("## References")[2]
    for reference in REFERENCES:
        doi = re.search(r"doi:(\S+)", reference).group(1)
        assert doi in reviewed, doi


def test_the_poster_renders_at_print_size_with_every_section_in_its_band(tmp_path):
    bottoms = poster.render(tmp_path / "poster.png", tmp_path / "preview.png")
    with Image.open(tmp_path / "poster.png") as im:
        assert im.size == (poster.WIDTH, poster.HEIGHT)
        assert round(im.info["dpi"][0]) == poster.PRINT_DPI
    with Image.open(tmp_path / "preview.png") as im:
        assert im.width == poster.PREVIEW_WIDTH
    assert bottoms["lede"] < poster.COLUMN_TOP
    for column in ("column 1", "column 2", "column 3"):
        assert bottoms[column] < poster.CHECKS_TOP, column
    assert bottoms["checks"] < poster.FOOTER_TOP
