import pandas as pd
import pytest

from pipeline.schema_discovery import (
    assign_type_superclass,
    check_physical_extent,
    derive_connective_sets,
    voxels_to_micrometers,
)


def superclass_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "type": ["DNa01", "DNa01", "AN05B001", "AN05B001", "LC4", "SNxx01", "MIXED", "MIXED"],
            "superclass": [
                "descending_neuron", None, "ascending_neuron", "sensory_ascending",
                "visual_projection", "vnc_sensory", "ascending_neuron", "descending_neuron",
            ],
            "neurons": [2, 1, 4, 1, 70, 12, 3, 3],
        }
    )


def test_majority_superclass_and_share():
    types = assign_type_superclass(superclass_rows()).set_index("type")
    assert types.loc["DNa01", "superclass"] == "descending_neuron"
    assert types.loc["DNa01", "neurons"] == 3
    assert types.loc["DNa01", "majority_share"] == pytest.approx(2 / 3)
    assert types.loc["AN05B001", "superclass"] == "ascending_neuron"
    assert types.loc["LC4", "majority_share"] == 1


def test_superclass_ties_break_alphabetically():
    types = assign_type_superclass(superclass_rows()).set_index("type")
    assert types.loc["MIXED", "superclass"] == "ascending_neuron"
    assert types.loc["MIXED", "majority_share"] == pytest.approx(0.5)


def test_connective_sets_contain_only_descending_and_ascending_types():
    sets = derive_connective_sets(assign_type_superclass(superclass_rows()))
    assert sets == {"descending": ["DNa01"], "ascending": ["AN05B001", "MIXED"]}


def test_empty_connective_set_fails_loudly():
    rows = pd.DataFrame({"type": ["LC4"], "superclass": ["visual_projection"], "neurons": [5]})
    with pytest.raises(RuntimeError, match="empty"):
        derive_connective_sets(assign_type_superclass(rows))


def test_voxels_convert_to_micrometers_at_8_nm():
    assert voxels_to_micrometers([125_000, 0]).tolist() == [1000.0, 0.0]


def test_physical_extent_check_accepts_a_fly_cns_and_rejects_unit_errors():
    check_physical_extent({"x": 730, "y": 514, "z": 995})
    with pytest.raises(RuntimeError, match="outside"):
        check_physical_extent({"x": 730_000, "y": 514_000, "z": 995_000})
    with pytest.raises(RuntimeError, match="outside"):
        check_physical_extent({"x": 0.73, "y": 0.514, "z": 0.995})
    with pytest.raises(RuntimeError, match="too short"):
        check_physical_extent({"x": 400, "y": 300, "z": 500})
