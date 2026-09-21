import json

import pandas as pd
import pytest

from export.build_static_json import site_data
from pipeline.common import RESULTS

# Every top-level key the page reads, with the keys inside it that a section or a figure names directly.
SECTIONS = {
    "synapses": ("totals", "deciles", "groups"),
    "tradeoff": ("graph", "baseline", "sampling", "curves", "comparison"),
    "hubs": ("totals", "scopes", "correlations", "degree_bins", "partners"),
    "symmetry": ("totals", "pairs", "midline", "unpaired_sides", "wire_asymmetry", "cost_ratio_asymmetry"),
    "regions": ("totals", "top_regions", "small_world", "partition", "communities", "anatomy", "mirrored"),
}


@pytest.fixture(scope="module")
def data() -> dict:
    return site_data(pd.read_csv(RESULTS / "connective_price.csv"))


def result(name: str) -> dict:
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


def test_the_payload_carries_every_section_the_page_renders(data):
    for key, fields in SECTIONS.items():
        assert key in data, key
        for field in fields:
            assert field in data[key], f"{key}.{field}"


def test_the_length_deciles_and_groups_match_the_result_file(data):
    synapse_value = result("synapse_value")
    assert len(data["synapses"]["deciles"]) == synapse_value["totals"]["deciles"]
    assert data["synapses"]["deciles"][0]["synapses_per_um"] == (
        synapse_value["groups"]["all"]["deciles"][0]["synapses_per_um"]
    )
    assert set(data["synapses"]["groups"]) == set(synapse_value["groups"])


def test_every_removal_schedule_is_exported_at_every_sampled_point(data):
    tradeoff = result("length_tradeoff")
    points = tradeoff["sampling"]["points"]
    for name, curve in tradeoff["curves"].items():
        assert len(data["tradeoff"]["curves"][name]) == points == len(curve)
        assert data["tradeoff"]["curves"][name][-1]["efficiency_share"] == curve[-1]["efficiency_share"]
    # The random schedule is a mean of repeats, so the page can show its spread.
    assert "efficiency_share_sd" in data["tradeoff"]["curves"]["random, matched count"][0]


def test_the_hub_placement_correlations_and_partner_nulls_are_exported_whole(data):
    hub_placement = result("hub_placement")
    assert len(data["hubs"]["correlations"]) == len(hub_placement["correlations"])
    assert len(data["hubs"]["degree_bins"]) == len(hub_placement["degree_bins"])
    assert set(data["hubs"]["partners"]["scopes"]) == set(hub_placement["partners"]["scopes"])
    # The page shows a prefix of the extremes, which are saved furthest below their own null first.
    extremes, saved = data["hubs"]["partners"]["extremes"], hub_placement["partners"]["extremes"]
    assert extremes, "the types furthest below their own null are shown"
    assert [(r["cell_type"], r["side"], r["z_score"]) for r in extremes] == \
        [(r["cell_type"], r["side"], r["z_score"]) for r in saved[:len(extremes)]]


def test_the_neuropils_outside_a_pair_are_exported_rather_than_dropped(data):
    wire_symmetry = result("wire_symmetry")
    totals = data["symmetry"]["totals"]
    assert len(data["symmetry"]["pairs"]) == wire_symmetry["wire_asymmetry"]["pairs"]
    assert len(data["symmetry"]["midline"]) == totals["midline"]["neuropils"]
    assert len(data["symmetry"]["unpaired_sides"]) == totals["unpaired_sides"]["neuropils"]


def test_both_region_nulls_and_the_communities_are_exported(data):
    neuropil_network = result("neuropil_network")
    regions = data["regions"]
    assert set(regions["small_world"]["nulls"]) == set(neuropil_network["small_world"]["nulls"])
    assert len(regions["communities"]) == regions["partition"]["communities"]
    # The brain regions the wire groups with the nerve cord, which the section names one by one.
    cord = next(c for c in neuropil_network["communities"] if c["vnc_regions"])
    compartment = {row["neuropil"]: row["compartment"] for row in neuropil_network["regions"]}
    assert regions["brain_with_cord"] == [n for n in cord["members"] if compartment[n] == "brain"]


def test_the_sections_added_after_the_registered_tests_stay_a_small_part_of_the_payload(data):
    whole = len(json.dumps(data, separators=(",", ":")))
    added = sum(len(json.dumps({k: data[k]}, separators=(",", ":"))) for k in SECTIONS)
    assert added < 0.1 * whole, f"{added} of {whole} bytes"
