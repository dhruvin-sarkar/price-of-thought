"""Check the cable-length validation against its per-neuron table and the report."""

from scipy import stats

import pipeline.cable_length_validation as cable
from verify.common import close, regenerated_report, result_csv, result_json, result_text, run, same_text

# cable_length.csv is written with three decimals, so rank correlations can move in the last digits.
REL = 1e-3


def check() -> str:
    s = result_json("cable_length.json")
    frame = result_csv("cable_length.csv")
    assert s["sampled"] == sum(cable.STRATA.values()), f"{s['sampled']} sampled, strata sum {sum(cable.STRATA.values())}"
    assert s["analysed"] == len(frame) == s["sampled"] - s["without_skeleton"], "analysed count differs"
    assert frame["bodyId"].is_unique, "a neuron is sampled twice"
    counts = frame["superclass"].value_counts().to_dict()
    if s["without_skeleton"] == 0:
        assert counts == cable.STRATA, f"strata {counts} differ from the protocol {cable.STRATA}"
    assert (frame["cable_um"] > 0).all() and (frame["soma_to_output_um"] >= 0).all(), "non-positive cable or distance"

    rho, p = stats.spearmanr(frame["soma_to_output_um"], frame["cable_um"], alternative="greater")
    assert close([s["spearman_rho"], s["p_value"]], [rho, p], rel=REL), "overall correlation differs from the table"
    assert s["significant"] == (s["p_value"] < cable.ALPHA), "significance flag"
    for superclass, part in frame.groupby("superclass"):
        c = s["by_superclass"][superclass]
        r, _ = stats.spearmanr(part["soma_to_output_um"], part["cable_um"])
        assert c["n"] == len(part) and close(c["spearman_rho"], r, rel=REL, abs_tol=1e-3), f"{superclass}: rho differs"
        assert close(c["median_cable_um"], part["cable_um"].median(), rel=REL), f"{superclass}: median cable differs"

    expected = regenerated_report(cable, s)
    assert same_text(result_text("cable_length.md"), expected), "cable_length.md is out of date"
    return (f"{len(frame)} neurons in {len(counts)} strata; overall rho {s['spearman_rho']:.3f} and every per-class "
            f"figure reproduced from the table; report current")


if __name__ == "__main__":
    run(check)
