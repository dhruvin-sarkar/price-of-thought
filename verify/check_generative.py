"""Check the generative model fits, the synthetic-graph comparison against its table, and the joint report."""

import tempfile
from pathlib import Path

import numpy as np

import pipeline.generative_comparison as comparison
import pipeline.generative_model as model
from verify.common import close, regenerated_report, result_csv, result_json, result_text, run, same_text

# generative_comparison.csv is written with six significant digits.
REL = 1e-5


def check_fits(s: dict) -> None:
    assert s["negatives"] == model.NEGATIVES_PER_EDGE * s["edges"], "negative sample size differs from the protocol"
    assert s["all_non_edges"] == s["nodes"] * (s["nodes"] - 1) - s["edges"], "non-edge count arithmetic"
    assert close(s["intercept_correction"], np.log(s["negatives"] / s["all_non_edges"])), "intercept correction"
    assert list(s["models"]) == list(model.MODELS), f"models {list(s['models'])}"
    previous = None
    for name, m in s["models"].items():
        assert close(m["pseudo_r2_mcfadden"], 1 - m["log_likelihood"] / m["log_likelihood_intercept_only"]), name
        assert close(m["aic"], 2 * m["parameters"] - 2 * m["log_likelihood"]), f"{name}: AIC arithmetic"
        assert len(m["cv_auc"]) == model.CV_FOLDS and close(m["cv_auc_mean"], np.mean(m["cv_auc"])), f"{name}: CV AUC"
        assert close(m["intercept_corrected"], m["intercept"] + s["intercept_correction"]), f"{name}: intercept"
        if previous is not None:
            assert m["log_likelihood"] >= previous, f"{name}: a nested model fits worse than the one it extends"
        previous = m["log_likelihood"]


def check_comparison(c: dict, table, fits: dict, real_refs: dict) -> None:
    assert c["n_synthetic"] == comparison.N_SYNTHETIC, f"{c['n_synthetic']} synthetic graphs per model"
    for name in comparison.MODELS:
        assert close(c["shifts"][name], fits["models"][name]["shift_to_match_edges"]), f"{name}: shift"
        subset = table[table["model"] == name]
        assert len(subset) == comparison.N_SYNTHETIC and sorted(subset["index"]) == list(range(comparison.N_SYNTHETIC))
        entry = c["models"][name]
        assert close(entry["edges"]["mean"], subset["edges"].mean(), rel=REL), f"{name}: edges"
        assert set(entry["properties"]) == set(comparison.PROPERTIES), f"{name}: properties"
        for prop, p in entry["properties"].items():
            lo, hi = np.percentile(subset[prop], [2.5, 97.5])
            assert close(p["interval_95"], [lo, hi], rel=REL) and close(p["synthetic_mean"], subset[prop].mean(),
                                                                        rel=REL), f"{name} {prop}: interval or mean"
            assert p["reproduced"] == bool(p["interval_95"][0] <= p["real"] <= p["interval_95"][1]), \
                f"{name} {prop}: reproduced flag"
        reproduced = sum(p["reproduced"] for p in entry["properties"].values())
        assert close(entry["fraction_reproduced"], reproduced / len(comparison.PROPERTIES)), f"{name}: fraction"
    for prop, expected in real_refs.items():
        assert close(c["models"]["G"]["properties"][prop]["real"], expected), \
            f"real {prop} differs from the analysis that measured it"


def check() -> str:
    fits = result_json("generative_model.json")
    comp = result_json("generative_comparison.json")
    check_fits(fits)
    richclub = result_json("connective_richclub.json")
    value = result_json("connective_value.json")
    placement = result_json("spatial_optimality.json")["analyses"]["primary"]
    real_refs = {"rich_routes": richclub["routes_top10"]["total"]["real"], "flow": value["intact"]["flow"],
                 "pairs": value["intact"]["pairs"], "neck_crossing_edges": value["removal_sets"]["crossing"]["edges"],
                 "total_cost_um": placement["real"]}
    assert comp["real_edges"] == fits["edges"], "the comparison and the fit use different graphs"
    check_comparison(comp, result_csv("generative_comparison.csv"), fits, real_refs)

    fitted = regenerated_report(model, fits)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "fit_only.md"
        base.write_text(fitted, encoding="utf-8")
        expected = regenerated_report(comparison, comp, report=base)
    assert same_text(result_text("generative_model.md"), expected), "generative_model.md is out of date"
    g, properties = comp["models"]["G"], len(comparison.PROPERTIES)
    return (f"{len(fits['models'])} nested fits consistent; {comparison.N_SYNTHETIC} graphs per model reproduce every "
            f"interval; model G reproduces {round(g['fraction_reproduced'] * properties)} of {properties}; real "
            f"values match the analyses that measured them; report current")


if __name__ == "__main__":
    run(check)
