"""Check the rich-club tests against the saved randomizations, the Fisher table and the report."""

import numpy as np
import pandas as pd
from scipy import stats

import pipeline.connective_richclub as richclub
from verify.common import close, regenerated_report, result_csv, result_json, result_text, run, same_text


def check() -> str:
    s = result_json("connective_richclub.json")
    nulls = result_csv("connective_richclub_nulls.csv")
    n = s["n_nulls"]
    assert n == richclub.N_NULLS and len(nulls) == n, f"{len(nulls)} randomizations saved, {n} recorded"
    assert s["n_graph_nulls"] == richclub.N_GRAPH_NULLS, f"{s['n_graph_nulls']} whole-graph randomizations"
    assert s["preregistration_commit"] == richclub.PREREGISTRATION_COMMIT

    top = richclub.TOP_FRACTION
    for key in ("total", "descending", "ascending"):
        recorded = s["routes_top10"][key]
        expected = richclub.compare(recorded["real"], nulls[f"{key}_{top}"].to_numpy())
        assert close(recorded, expected), f"routes {key} differ from the saved randomizations"
    total = s["routes_top10"]["total"]
    parts = s["routes_top10"]["descending"]["real"] + s["routes_top10"]["ascending"]["real"]
    assert total["real"] == parts, "descending and ascending routes do not add up to the total"
    for column in (c for c in nulls.columns if c.startswith("total_")):
        f = column.split("_", 1)[1]
        assert (nulls[column] == nulls[f"descending_{f}"] + nulls[f"ascending_{f}"]).all(), \
            f"randomized routes at {f} do not add up"

    curve = pd.DataFrame(s["threshold_curve"])
    assert list(curve["top_fraction"]) == list(richclub.THRESHOLDS), "threshold curve covers other thresholds"
    for row in curve.itertuples():
        values = nulls[f"total_{row.top_fraction}"].to_numpy()
        c = richclub.compare(row.real, values)
        assert close([row.null_mean, row.ratio, row.z_score, row.p_value],
                     [c["null_mean"], c["ratio"], c["z_score"], c["p_value"]]), \
            f"threshold {row.top_fraction} differs from the saved randomizations"
        assert close([row.ratio_lo, row.ratio_hi], list(np.percentile(values, [2.5, 97.5]) / c["null_mean"])), \
            f"threshold {row.top_fraction} interval differs"
    primary_row = curve[curve["top_fraction"] == top].iloc[0]
    assert close(primary_row["real"], total["real"]), "the curve's 10% point is not the primary statistic"

    e = s["endpoint_enrichment"]
    assert close(e["p_value"], (1 + e["n_at_or_above_real"]) / (1 + n)), "enrichment p != (1 + k) / (1 + N)"
    assert close([e["ratio"], e["z_score"]], [e["real"] / e["null_mean"], (e["real"] - e["null_mean"]) / e["null_sd"]]), \
        "enrichment ratio or z-score arithmetic"

    m = s["whole_cns_membership"]
    odds, p = stats.fisher_exact(m["table"], alternative="greater")
    assert close([odds, p], [m["odds_ratio"], m["p_value"]]), "Fisher test differs from its table"
    connective = m["table"][0][0] + m["table"][0][1]
    assert connective == sum(s["connective_nodes"].values()), "Fisher table does not hold every connective node"
    assert close(m["other_share_high"], m["table"][1][0] / (m["table"][1][0] + m["table"][1][1])), "other share"

    expected = regenerated_report(richclub, s, curve)
    assert same_text(result_text("connective_richclub.md"), expected), "connective_richclub.md is out of date"
    return (f"routes, {len(curve)} thresholds and enrichment reproduced from {n} randomizations; Fisher odds ratio "
            f"{m['odds_ratio']:.2f} from its table; report current")


if __name__ == "__main__":
    run(check)
