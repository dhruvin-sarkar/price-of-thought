"""Check the per-decile synapse accounting, the length correlations and the report against the saved result."""

import pipeline.synapse_value as synapse_value
from verify.common import close, result_json, result_text, run, same_text


def check() -> str:
    s = result_json("synapse_value.json")
    groups, totals = s["groups"], s["totals"]

    assert list(groups) == list(synapse_value.GROUPS), "the groups are in another order"
    whole, crossing, rest = groups["all"], groups["across the neck"], groups["elsewhere"]
    assert (whole["edges"], whole["synapses"]) == (totals["edges"], totals["synapses"]), \
        "the whole-graph group disagrees with the totals"
    assert close(whole["wire_um"], totals["wire_um"], rel=1e-9), "the whole-graph wire disagrees with the totals"
    # The neck-crossing connections and the rest partition the graph, unlike the views in wire_concentration.
    assert crossing["edges"] + rest["edges"] == whole["edges"], "the two halves do not add up"
    assert crossing["synapses"] + rest["synapses"] == whole["synapses"], "the two halves lose synapses"
    assert close(crossing["wire_um"] + rest["wire_um"], whole["wire_um"], rel=1e-6), "the two halves lose wire"

    for name, group in groups.items():
        assert close(group["synapses_per_um"], group["synapses"] / group["wire_um"], rel=1e-3), \
            f"{name} synapses per micrometre arithmetic"
        assert close(group["mean_synapses"], group["synapses"] / group["edges"], rel=1e-3), \
            f"{name} mean synapse count arithmetic"
        assert close(group["mean_length_um"], group["wire_um"] / group["edges"], rel=1e-3), \
            f"{name} mean length arithmetic"
        assert group["median_synapses"] >= 1, f"{name} median connection carries less than one synapse"
        correlation = group["correlation"]
        for key in ("spearman_rho", "pearson_log_r"):
            assert -1 <= correlation[key] <= 1, f"{name} {key} is not a correlation"
        for key in ("spearman_p", "pearson_log_p"):
            assert 0 <= correlation[key] <= 1, f"{name} {key} is not a probability"

        deciles = group["deciles"]
        assert [r["decile"] for r in deciles] == list(range(1, len(deciles) + 1)), f"{name} deciles are not in order"
        assert len(deciles) <= totals["deciles"], f"{name} has more deciles than asked for"
        assert sum(r["edges"] for r in deciles) == group["edges"], f"{name} deciles do not cover every connection"
        assert sum(r["synapses"] for r in deciles) == group["synapses"], f"{name} deciles lose synapses"
        assert close(sum(r["edges"] * r["mean_length_um"] for r in deciles), group["wire_um"], rel=1e-4), \
            f"{name} deciles do not hold the group's wire"
        for row in deciles:
            assert row["min_length_um"] <= row["mean_length_um"] <= row["max_length_um"], \
                f"{name} decile {row['decile']} lengths are out of order"
            assert close(row["synapses_per_um"], row["synapses"] / (row["edges"] * row["mean_length_um"]),
                         rel=2e-3), f"{name} decile {row['decile']} density arithmetic"
            assert close(row["expected_per_um"], group["mean_synapses"] / row["mean_length_um"], rel=2e-3), \
                f"{name} decile {row['decile']} expected density arithmetic"
            assert close(row["observed_over_expected"], row["synapses_per_um"] / row["expected_per_um"],
                         rel=2e-3), f"{name} decile {row['decile']} observed against expected arithmetic"
        for key in ("min_length_um", "mean_length_um", "max_length_um"):
            bounds = [r[key] for r in deciles]
            assert bounds == sorted(bounds), f"{name} deciles are not ordered by {key}"
        # Equal-count bins split at quantiles, so no connection can sit in two deciles.
        for lower, upper in zip(deciles, deciles[1:]):
            assert lower["max_length_um"] <= upper["min_length_um"] + 0.01, \
                f"{name} deciles {lower['decile']} and {upper['decile']} overlap"
        # Bins are cut at quantiles, so ties at a boundary can leave them slightly uneven.
        nominal = group["edges"] / len(deciles)
        for row in deciles:
            assert abs(row["edges"] - nominal) <= 0.05 * nominal, \
                f"{name} decile {row['decile']} holds far from a tenth of the connections"
        assert close(group["longest_over_shortest_per_um"],
                     deciles[-1]["synapses_per_um"] / deciles[0]["synapses_per_um"], rel=1e-3), \
            f"{name} longest against shortest density arithmetic"
        assert close(group["longest_over_shortest_median"],
                     deciles[-1]["median_synapses"] / deciles[0]["median_synapses"], rel=1e-3), \
            f"{name} longest against shortest median arithmetic"

    assert crossing["mean_length_um"] > rest["mean_length_um"], \
        "the neck-crossing connections are no longer the long ones"
    assert same_text(result_text("synapse_value.md"), synapse_value.report(s)), "synapse_value.md is out of date"
    rho = whole["correlation"]["spearman_rho"]
    return (f"{whole['edges']:,} connections hold {whole['synapses']:,} synapses at "
            f"{whole['synapses_per_um']:.3f} per um; shortest decile "
            f"{whole['deciles'][0]['synapses_per_um']:.2f} against {whole['deciles'][-1]['synapses_per_um']:.2f} "
            f"in the longest, median synapse count {whole['longest_over_shortest_median']:.2f}x, length against "
            f"synapse count rho {rho:+.3f}; report current")


if __name__ == "__main__":
    run(check)
