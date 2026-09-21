"""Check the centrality correlations, the partner-centroid test and the report against the saved result."""

import pipeline.hub_placement as hub_placement
from verify.common import close, result_json, result_text, run, same_text


def check() -> str:
    s = result_json("hub_placement.json")
    scopes, correlations, bins = s["scopes"], s["correlations"], s["degree_bins"]
    partners, totals = s["partners"], s["totals"]

    assert [r["scope"] for r in scopes] == list(hub_placement.SCOPES), "the scopes are in another order"
    sizes = {r["scope"]: r["types"] for r in scopes}
    assert sizes["all"] == totals["types"], "the whole-graph scope covers a different number of types"
    assert sizes["brain"] + sizes["nerve cord"] <= sizes["all"], "the two compartments hold more types than exist"
    for row in scopes:
        assert len(row["centroid_um"]) == 3, f"{row['scope']} centroid is not a point in space"
        assert 0 < row["median_distance_um"] <= row["max_distance_um"], f"{row['scope']} distances are out of order"

    expected = [(scope, measure) for scope in hub_placement.SCOPES for measure in ("degree", "wire")]
    assert [(r["scope"], r["measure"]) for r in correlations] == expected, "the correlations are in another order"
    for row in correlations:
        assert row["types"] == sizes[row["scope"]], f"{row['scope']} {row['measure']} covers another set of types"
        for key in ("spearman_rho", "pearson_log_r"):
            assert -1 <= row[key] <= 1, f"{row['scope']} {row['measure']} {key} is not a correlation"
        for key in ("spearman_p", "pearson_log_p"):
            assert 0 <= row[key] <= 1, f"{row['scope']} {row['measure']} {key} is not a probability"

    for scope in hub_placement.SCOPES:
        rows = [r for r in bins if r["scope"] == scope]
        assert [r["bin"] for r in rows] == list(range(1, len(rows) + 1)), f"{scope} bins are not consecutive"
        assert len(rows) <= hub_placement.BINS, f"{scope} has more bins than asked for"
        assert sum(r["types"] for r in rows) == sizes[scope], f"{scope} bins do not cover every type"
        degrees = [r["median_value"] for r in rows]
        assert degrees == sorted(degrees), f"{scope} bins are not ordered by degree"

    assert list(partners["scopes"]) == list(hub_placement.SCOPES), "the partner test covers other scopes"
    assert partners["types_tested"] == totals["types"] - totals["isolated_types"], \
        "the partner test covers a different number of types"
    assert 0 <= partners["share_nearer_than_chance"] <= 1, "the share nearer than chance is not a share"
    for scope, test in partners["scopes"].items():
        assert test["permutations"] == hub_placement.PERMUTATIONS, f"{scope} ran another number of draws"
        assert test["real_um"] > 0 and test["null_mean_um"] > 0, f"{scope} distances are not positive"
        assert close(test["ratio"], test["real_um"] / test["null_mean_um"], rel=1e-3), f"{scope} ratio arithmetic"
        assert close(test["z_score"], (test["real_um"] - test["null_mean_um"]) / test["null_sd_um"], rel=1e-2), \
            f"{scope} z-score arithmetic"
        assert 0 <= test["n_at_or_below_real"] <= test["permutations"], f"{scope} rank out of range"
        assert close(test["p_value"], (1 + test["n_at_or_below_real"]) / (1 + test["permutations"]), rel=1e-3), \
            f"{scope} p-value arithmetic"

    extremes = partners["extremes"]
    assert extremes, "no type is listed among the extremes"
    assert len(extremes) <= hub_placement.EXTREMES, "more extremes are listed than asked for"
    assert [r["z_score"] for r in extremes] == sorted(r["z_score"] for r in extremes), \
        "the extremes are not ordered by z-score"
    for row in extremes:
        assert row["degree"] > 0, f"{row['cell_type']}|{row['side']} is listed with no connection"
        assert row["z_score"] < 0, f"{row['cell_type']}|{row['side']} sits further from its partners than chance"
        assert row["distance_to_partners_um"] > 0, f"{row['cell_type']}|{row['side']} distance is not positive"

    assert same_text(result_text("hub_placement.md"), hub_placement.report(s)), "hub_placement.md is out of date"
    degree = {r["scope"]: r["spearman_rho"] for r in correlations if r["measure"] == "degree"}
    strongest = max(abs(v) for v in degree.values())
    whole = partners["scopes"]["all"]
    return (f"degree against distance from the centre reproduced for {len(scopes)} scopes, strongest rho "
            f"{strongest:.3f}; partner-centroid distance {whole['real_um']:.1f} um against "
            f"{whole['null_mean_um']:.1f} um over {whole['permutations']} draws "
            f"(ratio {whole['ratio']:.3f}, z {whole['z_score']:.1f}); report current")


if __name__ == "__main__":
    run(check)
