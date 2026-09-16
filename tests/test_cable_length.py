import numpy as np
import pandas as pd
import pytest

from pipeline.cable_length_validation import cable_length_um, stratified_sample


def test_cable_length_sums_segments_and_skips_fragment_roots():
    skeleton = pd.DataFrame({
        "rowId": [1, 2, 3, 4, 5],
        "x": [0, 3, 3, 1000, 1000],
        "y": [0, 4, 4, 0, 0],
        "z": [0, 0, 10, 0, 125],
        "link": [-1, 1, 2, -1, 4],
    })
    # Segments of 5, 10 and 125 voxels; the jump to the second root is not cable.
    assert cable_length_um(skeleton, voxel_nm=8.0) == pytest.approx(140 * 8 / 1000)


def test_stratified_sample_sizes_and_reproducibility():
    candidates = pd.DataFrame({"bodyId": np.arange(300), "superclass": ["a"] * 200 + ["b"] * 100})
    first = stratified_sample(candidates, {"a": 20, "b": 10}, seed=5)
    again = stratified_sample(candidates.sample(frac=1, random_state=1), {"a": 20, "b": 10}, seed=5)
    assert first["superclass"].value_counts().to_dict() == {"a": 20, "b": 10}
    assert first["bodyId"].is_unique
    assert first["bodyId"].tolist() == again["bodyId"].tolist()
    with pytest.raises(ValueError):
        stratified_sample(candidates, {"b": 101}, seed=5)
