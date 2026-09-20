"""Check the per-neuropil wire accounting, its placement tests and the report against the saved result."""

import pipeline.wire_atlas as wire_atlas
from verify.common import close, result_json, result_text, run, same_text


def check() -> str:
    s = result_json("wire_atlas.json")
    rows, pairs, totals = s["neuropils"], s["pairs"], s["totals"]

    assert totals["permutations"] == wire_atlas.PERMUTATIONS
    assert totals["neuropils_with_types"] == len(rows), "totals disagree with the rows saved"
    assert totals["meshes"] >= totals["neuropils_with_types"], "more neuropils hold types than there are meshes"
    assert [r["wire_um"] for r in rows] == sorted((r["wire_um"] for r in rows), reverse=True), \
        "the neuropils are not ordered by the wire they hold"

    # Each connection lends half its length to the neuropil at each end, so the shares add to one.
    assert close(sum(r["wire_um"] for r in rows), totals["total_wire_um"], rel=1e-4), \
        "the wire attributed to the neuropils does not add up to the total"
    assert close(sum(r["wire_share"] for r in rows), 1.0, rel=1e-3), "the shares do not add to one"
    for row in rows:
        # The share is saved to six decimals, so the smallest neuropils only match to within half of one.
        assert close(row["wire_share"], row["wire_um"] / totals["total_wire_um"], rel=1e-3, abs_tol=1e-6), \
            f"{row['neuropil']} share does not match its wire"
        assert row["types"] > 0, f"{row['neuropil']} is listed with no cell types"
        assert row["edges_internal"] <= row["edges_incident"], \
            f"{row['neuropil']} holds more internal connections than it touches"

    tested = [r for r in rows if "cost_ratio" in r]
    assert tested, "no neuropil got a placement test"
    for row in tested:
        assert row["types"] >= wire_atlas.MIN_TYPES and row["edges_internal"] >= wire_atlas.MIN_INTERNAL_EDGES, \
            f"{row['neuropil']} was tested below the size floor"
        assert close(row["cost_ratio"], row["internal_real_um"] / row["internal_null_mean_um"], rel=1e-3), \
            f"{row['neuropil']} cost ratio arithmetic"
        expected_z = (row["internal_real_um"] - row["internal_null_mean_um"]) / row["internal_null_sd_um"]
        assert close(row["z_score"], expected_z, rel=1e-2), f"{row['neuropil']} z-score arithmetic"
        assert 0 <= row["n_at_or_below_real"] <= wire_atlas.PERMUTATIONS, f"{row['neuropil']} rank out of range"

    internal = sum(r["internal_real_um"] for r in tested)
    assert internal <= totals["wire_within_one_neuropil_um"] + 1, \
        "the tested neuropils hold more internal wire than the whole specimen does"
    assert close(totals["share_within_one_neuropil"],
                 totals["wire_within_one_neuropil_um"] / totals["total_wire_um"], rel=1e-3), \
        "the share staying inside one neuropil does not match its wire"

    named = {r["neuropil"] for r in rows}
    for pair in pairs:
        assert pair["a"] in named and pair["b"] in named, f"{pair['a']}-{pair['b']} names a neuropil with no types"
    assert [p["wire_um"] for p in pairs] == sorted((p["wire_um"] for p in pairs), reverse=True), \
        "the pairs are not ordered by the wire between them"
    for pair in (p for p in pairs if p["a"] == p["b"]):
        row = next(r for r in rows if r["neuropil"] == pair["a"])
        assert pair["edges"] == row["edges_internal"], f"{pair['a']} pair count differs from its internal count"

    assert same_text(result_text("wire_atlas.md"), wire_atlas.report(s)), "wire_atlas.md is out of date"
    cheapest = min(tested, key=lambda r: r["cost_ratio"])
    return (f"{len(rows)} neuropils hold {totals['total_wire_um'] / 1e6:.1f} m of wire, {len(tested)} placement "
            f"tests reproduced, most economical {cheapest['neuropil']} at {cheapest['cost_ratio']:.3f}; report current")


if __name__ == "__main__":
    run(check)
