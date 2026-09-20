"""Check the hemisphere pairing, the two asymmetry nulls and the report against the saved result."""

import math

import pipeline.wire_symmetry as wire_symmetry
from verify.common import close, result_json, result_text, run, same_text


def check() -> str:
    s = result_json("wire_symmetry.json")
    atlas = {row["neuropil"]: row for row in result_json("wire_atlas.json")["neuropils"]}
    pairs, totals, wire = s["pairs"], s["totals"], s["wire_asymmetry"]

    assert totals["neuropils"] == len(atlas), "the atlas holds another number of neuropils"
    assert totals["permutations"] == wire_symmetry.PERMUTATIONS
    covered = ([f"{r['neuropil']}(L)" for r in pairs] + [f"{r['neuropil']}(R)" for r in pairs]
               + [r["neuropil"] for r in s["midline"]] + [r["neuropil"] for r in s["unpaired_sides"]])
    assert sorted(covered) == sorted(atlas), "the three groups do not partition the atlas"

    for row in pairs:
        for side, suffix in (("left", "L"), ("right", "R")):
            source = atlas[f"{row['neuropil']}({suffix})"]
            # Every number in the pair table is read from the atlas, so it must still be the atlas's number.
            assert row[f"wire_{side}_um"] == source["wire_um"], f"{row['neuropil']}({suffix}) wire was rewritten"
            assert row[f"wire_share_{side}"] == source["wire_share"], f"{row['neuropil']}({suffix}) share"
            assert row[f"types_{side}"] == source["types"], f"{row['neuropil']}({suffix}) cell types"
        # A pair carries cost ratios only when the atlas tested both of its sides.
        both = all("cost_ratio" in atlas[f"{row['neuropil']}({s})"] for s in "LR")
        assert ("cost_ratio_left" in row) == both, f"{row['neuropil']} cost ratios do not follow the atlas"
        if both:
            for side, suffix in (("left", "L"), ("right", "R")):
                assert row[f"cost_ratio_{side}"] == atlas[f"{row['neuropil']}({suffix})"]["cost_ratio"], \
                    f"{row['neuropil']}({suffix}) cost ratio was rewritten"
        assert close(row["log_ratio"], math.log(row["wire_left_um"] / row["wire_right_um"]), abs_tol=1e-4), \
            f"{row['neuropil']} log ratio arithmetic"
        if "cost_ratio_difference" in row:
            assert close(row["cost_ratio_difference"], row["cost_ratio_left"] - row["cost_ratio_right"],
                         abs_tol=1e-4), f"{row['neuropil']} cost ratio difference arithmetic"
    combined = [r["wire_left_um"] + r["wire_right_um"] for r in pairs]
    assert combined == sorted(combined, reverse=True), "the pairs are not ordered by the wire they hold"

    for name in ("midline", "unpaired_sides"):
        assert [r["wire_um"] for r in s[name]] == sorted((r["wire_um"] for r in s[name]), reverse=True), \
            f"the {name} neuropils are not ordered by the wire they hold"
        for row in s[name]:
            source = atlas[row["neuropil"]]
            assert (row["wire_um"], row["types"]) == (source["wire_um"], source["types"]), \
                f"{row['neuropil']} was rewritten"
    for row in s["unpaired_sides"]:
        stem, side = wire_symmetry.split_side(row["neuropil"])
        assert side is not None, f"{row['neuropil']} is listed as one side but carries no side"
        assert f"{stem}({'R' if side == 'L' else 'L'})" not in atlas, f"{row['neuropil']} does have a partner"
    for row in s["midline"]:
        assert wire_symmetry.split_side(row["neuropil"])[1] is None, f"{row['neuropil']} carries a side"

    assert totals["paired"]["neuropils"] == 2 * len(pairs), "the paired count disagrees with the pair table"
    assert close(totals["paired"]["wire_um"], sum(combined), rel=1e-6), "the paired wire does not add up"
    parts = sum(totals[k]["wire_um"] for k in ("paired", "midline", "unpaired_sides"))
    assert close(parts, totals["total_wire_um"], rel=1e-6), "the three groups do not hold the whole budget"
    assert close(sum(totals[k]["wire_share"] for k in ("paired", "midline", "unpaired_sides")), 1.0,
                 abs_tol=2e-4), "the three shares do not add to one"

    tests = [("wire", wire)] + ([("cost ratio", s["cost_ratio_asymmetry"])] if s["cost_ratio_asymmetry"] else [])
    for name, test in tests:
        assert test["permutations"] == wire_symmetry.PERMUTATIONS, f"the {name} test ran another number of flips"
        assert abs(test["mean"]) <= test["mean_absolute"] + 1e-4, f"the {name} mean exceeds its absolute mean"
        assert test["median_absolute"] <= test["max_absolute"] + 1e-4, f"the {name} median exceeds its maximum"
        assert test["mean_absolute"] <= test["max_absolute"] + 1e-4, f"the {name} mean exceeds its maximum"
        assert close(test["z_score"], test["mean"] / test["null_sd"], rel=1e-2, abs_tol=5e-3), \
            f"the {name} z-score arithmetic"
        assert 1 / (test["permutations"] + 1) <= test["p_value"] <= 1, f"the {name} p-value is out of range"
    assert wire["pairs"] == len(pairs), "the wire test covers another number of pairs"
    assert s["cost_ratio_asymmetry"]["pairs"] == sum("cost_ratio_difference" in r for r in pairs), \
        "the cost ratio test covers another number of pairs"
    assert close(wire["repaired_p_value"],
                 (1 + wire["repaired_n_at_or_below_observed"]) / (1 + wire["permutations"]), rel=1e-3), \
        "the random-matching p-value arithmetic"
    assert 0 <= wire["repaired_n_at_or_below_observed"] <= wire["permutations"], "the random-matching rank"

    assert same_text(result_text("wire_symmetry.md"), wire_symmetry.report(s)), "wire_symmetry.md is out of date"
    widest = max(pairs, key=lambda r: abs(r["log_ratio"]))
    return (f"{len(pairs)} pairs, {len(s['midline'])} midline and {len(s['unpaired_sides'])} one-sided "
            f"neuropils partition the atlas; median wire ratio {math.exp(wire['median_absolute']):.2f}x, widest "
            f"{widest['neuropil']} at {math.exp(abs(widest['log_ratio'])):.1f}x; side bias p "
            f"{wire['p_value']:.4f}, against random matching p {wire['repaired_p_value']:.4f}; report current")


if __name__ == "__main__":
    run(check)
