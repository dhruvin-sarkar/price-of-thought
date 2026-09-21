import importlib
import json

import pytest

from pipeline.common import RESULTS

# Every module that draws a committed PNG from its own result file through a ``figure(result, path)``.
DRAWN = ("hub_placement", "length_tradeoff", "neuropil_network", "synapse_value", "wire_atlas",
         "wire_concentration", "wire_symmetry")


@pytest.mark.parametrize("name", DRAWN)
def test_every_result_figure_redraws_from_its_committed_result(name, tmp_path):
    module = importlib.import_module(f"pipeline.{name}")
    result = json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))
    path = tmp_path / f"{name}.png"

    module.figure(result, path)
    drawn = path.read_bytes()

    assert drawn[:8] == b"\x89PNG\r\n\x1a\n"
    # A blank canvas is a few kilobytes; every one of these panels is far heavier than that.
    assert len(drawn) > 20_000, len(drawn)
    # Rasterization differs between matplotlib builds, so the committed file is compared on canvas size
    # alone: bytes 16 to 24 are the width and height the IHDR chunk records.
    assert drawn[16:24] == (RESULTS / f"{name}.png").read_bytes()[16:24], "the committed figure has another size"
