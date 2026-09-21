import math

import numpy as np
import pytest

from pipeline.wire_symmetry import (
    PERMUTATIONS,
    bias_test,
    pair_rows,
    pair_up,
    repairing_null,
    report,
    sign_flip_null,
    split_side,
    symmetry,
    two_sided_p,
)


def neuropil(name: str, wire: float, types: int = 100, compartment: str = "brain", **extra) -> dict:
    """One row of the wire atlas, with the share it would hold of a 1,000,000 µm budget."""
    return {"neuropil": name, "compartment": compartment, "types": types, "edges_incident": 10 * types,
            "wire_um": wire, "wire_share": round(wire / 1e6, 6), "edges_internal": types, **extra}


def atlas(rows: list[dict]) -> dict:
    """A wire atlas holding the rows given, with a total that matches them."""
    return {"neuropils": rows, "pairs": [], "totals": {"total_wire_um": 1e6, "permutations": 1000}}


@pytest.mark.parametrize(("name", "expected"), [
    ("AVLP(L)", ("AVLP", "L")),
    ("LegNp(T2)(R)", ("LegNp(T2)", "R")),
    ("HTct(UTct-T3)(L)", ("HTct(UTct-T3)", "L")),
    ("b'L(L)", ("b'L", "L")),
    ("GNG", ("GNG", None)),
    ("CV-anterior", ("CV-anterior", None)),
    ("IntTct", ("IntTct", None)),
])
def test_split_side_takes_only_a_trailing_hemisphere_suffix(name, expected):
    assert split_side(name) == expected


def test_pair_up_separates_pairs_from_midline_structures_and_lone_sides():
    rows = [neuropil("AL(L)", 300.0), neuropil("AL(R)", 200.0), neuropil("GNG", 900.0),
            neuropil("VES(R)", 50.0), neuropil("LO(R)", 100.0), neuropil("LO(L)", 120.0)]
    pairs, midline, unpaired = pair_up(rows)

    assert [p["neuropil"] for p in pairs] == ["AL", "LO"]  # ordered by the wire the two sides hold together
    assert (pairs[0]["left"]["neuropil"], pairs[0]["right"]["neuropil"]) == ("AL(L)", "AL(R)")
    assert [r["neuropil"] for r in midline] == ["GNG"]
    assert [r["neuropil"] for r in unpaired] == ["VES(R)"]


def test_pair_rows_reads_both_sides_from_the_atlas_and_logs_their_ratio():
    pairs, _, _ = pair_up([neuropil("AL(L)", 200.0, types=7, cost_ratio=0.8),
                           neuropil("AL(R)", 100.0, types=5, cost_ratio=0.5)])
    row = pair_rows(pairs)[0]

    assert (row["wire_left_um"], row["wire_right_um"]) == (200.0, 100.0)
    assert (row["types_left"], row["types_right"]) == (7, 5)
    assert row["log_ratio"] == pytest.approx(math.log(2), abs=5e-5)
    assert row["cost_ratio_difference"] == pytest.approx(0.3)


def test_a_pair_carries_cost_ratios_only_when_the_atlas_tested_both_sides():
    pairs, _, _ = pair_up([neuropil("AL(L)", 200.0, cost_ratio=0.8), neuropil("AL(R)", 100.0)])
    assert "cost_ratio_left" not in pair_rows(pairs)[0]


def test_sign_flip_null_is_centred_on_zero_and_reproducible():
    values = np.array([0.4, -0.2, 0.9, -0.5, 0.1])
    null = sign_flip_null(values, seed=3)
    assert len(null) == PERMUTATIONS
    assert abs(null.mean()) < np.abs(values).mean()
    assert null.max() <= np.abs(values).mean() + 1e-12
    np.testing.assert_array_equal(null, sign_flip_null(values, seed=3))
    assert not np.array_equal(null, sign_flip_null(values, seed=4))


def test_flipping_the_sign_of_a_balanced_pair_changes_nothing():
    assert sign_flip_null(np.zeros(6), seed=1).tolist() == [0.0] * PERMUTATIONS


def test_repairing_null_is_zero_when_every_neuropil_holds_the_same_wire():
    same = np.full(8, 400.0)
    assert repairing_null(same, same, seed=5).tolist() == [0.0] * PERMUTATIONS


def test_repairing_null_grows_when_the_neuropils_differ_in_size():
    sizes = np.array([1.0, 10.0, 100.0, 1000.0])
    null = repairing_null(sizes, sizes, seed=6)
    assert len(null) == PERMUTATIONS
    assert (null >= 0).all()
    # Matching a neuropil to itself is the only pairing with no gap, and three of the four must then move.
    assert null.mean() > 0


def test_two_sided_p_counts_the_null_at_least_as_far_from_zero():
    null = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    assert two_sided_p(0.5, null) == pytest.approx(5 / 6)
    assert two_sided_p(1.5, null) == pytest.approx(3 / 6)
    assert two_sided_p(9.0, null) == pytest.approx(1 / 6)
    # A draw exactly as far from zero as the observed value counts towards it.
    assert two_sided_p(2.0, null) == pytest.approx(3 / 6)
    # Only the distance from zero counts, so the sign of the observed value makes no difference.
    assert two_sided_p(-1.5, null) == two_sided_p(1.5, null)


def test_bias_test_weighs_the_mean_against_the_spread_of_its_own_sign_flip_null():
    # Three pairs favour one side by 0.5 and one the other by 0.1: the mean is 0.35 and a sign-flip draw
    # reaches 0.4, 0.35, 0.15 or 0.1 in absolute value, so a quarter of the null sits at or beyond 0.35.
    values = np.array([0.5, 0.5, 0.5, -0.1])
    test = bias_test(values, seed=2)

    assert test["pairs"] == 4
    assert test["permutations"] == PERMUTATIONS
    assert test["mean"] == pytest.approx(0.35)
    assert (test["mean_absolute"], test["median_absolute"], test["max_absolute"]) == (0.4, 0.5, 0.5)
    assert test["null_sd"] == pytest.approx(math.sqrt((3 * 0.25 + 0.01) / 16), abs=0.02)
    assert test["z_score"] == pytest.approx(0.35 / math.sqrt((3 * 0.25 + 0.01) / 16), abs=0.1)
    assert test["p_value"] == pytest.approx(0.25, abs=0.05)


def test_bias_test_reports_no_bias_when_every_pair_is_exactly_in_balance():
    test = bias_test(np.array([0.5, -0.5, 0.5, -0.5]), seed=2)
    assert test["mean"] == 0.0
    assert (test["mean_absolute"], test["median_absolute"], test["max_absolute"]) == (0.5, 0.5, 0.5)
    assert test["z_score"] == 0.0
    assert test["p_value"] == 1.0


def test_symmetry_accounts_for_every_neuropil_of_the_atlas():
    rows = [neuropil("AL(L)", 400_000.0, cost_ratio=0.8), neuropil("AL(R)", 200_000.0, cost_ratio=0.6),
            neuropil("LO(L)", 150_000.0), neuropil("LO(R)", 150_000.0),
            neuropil("GNG", 90_000.0), neuropil("VES(R)", 10_000.0, compartment="vnc")]
    result = symmetry(atlas(rows))
    totals, wire = result["totals"], result["wire_asymmetry"]

    assert [r["neuropil"] for r in result["pairs"]] == ["AL", "LO"]
    assert [r["log_ratio"] for r in result["pairs"]] == pytest.approx([math.log(2), 0.0], abs=5e-5)
    assert totals["paired"] == {"neuropils": 4, "wire_um": 900_000.0, "wire_share": 0.9}
    assert totals["midline"] == {"neuropils": 1, "wire_um": 90_000.0, "wire_share": 0.09}
    assert totals["unpaired_sides"] == {"neuropils": 1, "wire_um": 10_000.0, "wire_share": 0.01}
    assert totals["neuropils"] == 6

    assert wire["pairs"] == 2
    assert wire["mean"] == pytest.approx(math.log(2) / 2, abs=5e-5)
    assert wire["mean_absolute"] == pytest.approx(math.log(2) / 2, abs=5e-5)
    assert wire["max_absolute"] == pytest.approx(math.log(2), abs=5e-5)
    assert result["cost_ratio_asymmetry"]["pairs"] == 1
    assert result["cost_ratio_asymmetry"]["mean"] == pytest.approx(0.2)


def test_a_perfectly_symmetric_atlas_shows_no_asymmetry_at_all():
    rows = [neuropil(f"{stem}({side})", 100_000.0) for stem in ("AL", "LO", "LH") for side in "LR"]
    wire = symmetry(atlas(rows))["wire_asymmetry"]
    assert wire["mean"] == 0.0
    assert wire["max_absolute"] == 0.0
    # Every neuropil holds the same wire, so no rematching of the two sides can open a gap either.
    assert wire["repaired_null_mean"] == 0.0
    assert wire["repaired_n_at_or_below_observed"] == PERMUTATIONS
    assert wire["repaired_p_value"] == 1.0


def test_matching_each_left_neuropil_to_a_random_right_one_opens_a_far_wider_gap():
    sizes = (("AL", (400_000.0, 380_000.0)), ("LO", (150_000.0, 160_000.0)),
             ("LH", (60_000.0, 58_000.0)), ("MB", (20_000.0, 21_000.0)))
    rows = [neuropil(f"{stem}({side})", wire) for stem, sides in sizes for side, wire in zip("LR", sides)]
    wire = symmetry(atlas(rows))["wire_asymmetry"]

    assert wire["pairs"] == 4
    assert wire["mean_absolute"] < 0.1
    # Matching AL against MB and the like opens gaps an order of magnitude wider than the real pairing.
    assert wire["repaired_null_mean"] > 10 * wire["mean_absolute"]
    assert wire["repaired_null_sd"] > 0
    # Only a redraw that rebuilds the true pairing is as tight as it, which over four pairs is the
    # 1 in 4! chance of drawing the identity permutation.
    at_or_below = wire["repaired_n_at_or_below_observed"]
    assert at_or_below == 41 == pytest.approx(PERMUTATIONS / 24, rel=0.2)
    assert wire["repaired_p_value"] == pytest.approx((at_or_below + 1) / (PERMUTATIONS + 1), abs=5e-7)
    # The sign-flip test asks whether one side is systematically larger, and finds nothing.
    assert wire["p_value"] > 0.5


def test_report_states_the_headline_numbers_it_was_given():
    rows = [neuropil("AL(L)", 400_000.0, cost_ratio=0.8), neuropil("AL(R)", 200_000.0, cost_ratio=0.6),
            neuropil("LO(L)", 150_000.0), neuropil("LO(R)", 150_000.0),
            neuropil("GNG", 90_000.0), neuropil("VES(R)", 10_000.0, compartment="vnc")]
    result = symmetry(atlas(rows))
    text = report(result)

    assert "# Wire symmetry" in text
    assert "Of the 6 neuropils that hold cell types, 4 form 2 left-right pairs and carry 90.00% of the wire" in text
    assert "the widest gap is AL, where the left copy holds 2.0 times the wire of the other" in text
    assert "| AL | brain | 100 | 100 | 400000.0 | 200000.0 |" in text
    assert "| GNG | brain | 100 | 90000.0 | 0.09 |" in text
    assert "| VES(R) | vnc | 100 | 10000.0 | 0.01 |" in text
    assert "1 neuropils carry no hemisphere suffix" in text
    assert "![Wire symmetry](wire_symmetry.png)" in text
