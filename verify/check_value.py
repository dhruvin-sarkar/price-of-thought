"""Check the connective value test: cost matching of every null set, every comparison, and the report."""

import pipeline.connective_value as value
from pipeline.connective_richclub import compare
from verify.common import close, regenerated_report, result_csv, result_json, result_text, run, same_text

METRICS = ("flow", "pairs", "flow_brain_to_vnc", "flow_vnc_to_brain")
# Every cost-matched set lands within one edge of its target; the longest non-connective edge is about 1 mm.
COST_TOLERANCE = 1e-4


def check() -> str:
    s = result_json("connective_value.json")
    nulls = result_csv("connective_value_nulls.csv")
    n = s["n_nulls"]
    assert n == value.N_NULLS and s["preregistration_commit"] == value.PREREGISTRATION_COMMIT
    assert set(s["families"]) == set(value.FAMILIES), f"families {sorted(s['families'])}"
    sets = s["sets"]
    assert sets["sensory"] == sets["sensory_brain"] + sets["sensory_vnc"], "sensory set does not split"
    assert sets["motor"] == sets["motor_brain"] + sets["motor_vnc"], "motor set does not split"

    intact, real, removal = s["intact"], s["real"], s["removal_sets"]
    for label, values in real.items():
        for metric in METRICS:
            assert 0 <= values[metric] <= intact[metric], f"removing {label} raised {metric}"

    for family in value.FAMILIES:
        subset = nulls[nulls["family"] == family].sort_values("index")
        assert len(subset) == n and (subset["index"].to_numpy() == range(n)).all(), f"{family}: null indices"
        target = "incident" if family.startswith("incident") else "crossing"
        ratio = subset["cost_removed"] / removal[target]["cost_um"]
        recorded = s["families"][family]
        assert close([ratio.min(), ratio.max()], [recorded["random_cost_ratio"]["min"],
                                                  recorded["random_cost_ratio"]["max"]]), f"{family}: cost ratios"
        if family.endswith("_cost"):
            assert (abs(ratio - 1) <= COST_TOLERANCE).all(), f"{family}: a null set is not cost-matched"
        else:
            assert (subset["edges_removed"] == removal[target]["edges"]).all(), f"{family}: a set is not count-matched"
        assert close(recorded["random_edges_removed"]["mean"], subset["edges_removed"].mean()), f"{family}: edge counts"
        for metric in METRICS:
            expected = compare(intact[metric] - real[target][metric], (intact[metric] - subset[metric]).to_numpy())
            assert close(recorded[metric], expected), f"{family} {metric} differs from the saved null sets"

    longest = removal["longest_non_connective"]
    assert longest["cost_um"] >= removal["crossing"]["cost_um"] and \
        longest["cost_um"] - removal["crossing"]["cost_um"] < longest["min_length_um"], \
        "the longest-edge set does not stop at the first edge that reaches the connective's cost"
    assert close(removal["crossing"]["mean_length_um"], removal["crossing"]["cost_um"] / removal["crossing"]["edges"])

    expected = regenerated_report(value, s)
    assert same_text(result_text("connective_value.md"), expected), "connective_value.md is out of date"
    primary = s["families"]["crossing_cost"]["flow"]
    return (f"{len(value.FAMILIES)} x {n} null sets matched to within {COST_TOLERANCE:.0e} of cost or exactly in count; "
            f"every comparison reproduced (primary ratio {primary['ratio']:.2f}); report current")


if __name__ == "__main__":
    run(check)
