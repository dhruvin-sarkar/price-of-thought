"""Check the per-cell-type price and value test against its node table, the connective totals and the report."""

from scipy import stats

import pipeline.connective_price as price
from verify.common import close, regenerated_report, result_csv, result_json, result_text, run, same_text

# connective_price.csv is written with two decimals.
REL = 1e-3


def check() -> str:
    s = result_json("connective_price.json")
    frame = result_csv("connective_price.csv")
    value = result_json("connective_value.json")
    crossing = value["removal_sets"]["crossing"]
    assert frame["node"].is_unique, "a node appears twice"
    assert s["intact"] == {k: value["intact"][k] for k in s["intact"]}, "intact flow differs from connective_value.json"

    # Each neck-crossing edge has exactly one connective endpoint, so per-node prices partition the connective.
    assert frame["edges"].sum() == crossing["edges"], "per-node edges do not add up to the neck-crossing edges"
    assert close(frame["price_um"].sum(), crossing["cost_um"], rel=1e-6), "per-node prices do not add up to its cost"
    for metric in ("flow", "flow_brain_to_vnc", "flow_vnc_to_brain"):
        lost = frame[f"lost_{metric}"]
        assert (lost >= 0).all() and (lost <= s["intact"][metric]).all(), f"lost {metric} outside [0, intact]"
    expected_value = frame["lost_flow_brain_to_vnc"].where(frame["direction"] == "descending",
                                                           frame["lost_flow_vnc_to_brain"])
    assert (frame["value"] == expected_value).all(), "value is not the flow in the node's own direction"

    for group in price.DIRECTION:
        part = frame[frame["direction"] == group]
        t = s["tests"][group]
        rho = stats.spearmanr(part["price_um"], part["value"], alternative="greater")
        partial_rho, partial_p = price.partial_spearman(part["price_um"].to_numpy(), part["value"].to_numpy(),
                                                        part["edges"].to_numpy())
        assert (t["n"], t["zero_value"], t["total_value"]) == (len(part), int((part["value"] == 0).sum()),
                                                                int(part["value"].sum())), f"{group}: counts differ"
        assert close([t["spearman_rho"], t["partial_rho"]], [rho.statistic, partial_rho], rel=REL, abs_tol=1e-4), \
            f"{group}: correlations differ from the table"
        assert close([t["p_value"], t["partial_p_value"]], [rho.pvalue, partial_p], rel=1e-2, abs_tol=1e-4), \
            f"{group}: p-values differ from the table"
    assert s["h10_supported"] == all(t["p_value"] < price.ALPHA for t in s["tests"].values()), "H10 flag"
    assert s["h10b_supported"] == all(t["partial_p_value"] < price.ALPHA for t in s["tests"].values()), "H10b flag"

    expected = regenerated_report(price, s, frame)
    assert same_text(result_text("connective_price.md"), expected), "connective_price.md is out of date"
    return (f"{len(frame):,} nodes whose prices sum to the {crossing['edges']:,} neck-crossing edges; correlations and "
            f"partial correlations reproduced; report current")


if __name__ == "__main__":
    run(check)
