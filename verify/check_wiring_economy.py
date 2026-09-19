"""Check the wiring-economy extensions against the distance table, the other results and the report."""

import numpy as np
from scipy import stats

import pipeline.wiring_economy_extensions as economy
from verify.common import close, regenerated_report, result_csv, result_json, result_text, run, same_text


def check() -> str:
    s = result_json("wiring_economy_extensions.json")
    table = result_csv("distance_dependence.csv")
    graph = result_json("spatial_graph_summary.json")["spatial_graph"]
    placement = result_json("spatial_optimality.json")["analyses"]["primary"]
    value = result_json("connective_value.json")["removal_sets"]

    n, n_edges = graph["nodes"], graph["edges"]
    assert table["pairs_all"].sum() == n * (n - 1), "distance bins do not hold every ordered pair"
    assert table["edges_all"].sum() == n_edges, "distance bins do not hold every edge"
    for kind in ("pairs", "edges"):
        parts = sum(table[f"{kind}_{c}"] for c in ("brain-brain", "vnc-vnc", "cross"))
        assert (parts == table[f"{kind}_all"]).all(), f"{kind} by compartment do not add up per bin"

    centres = table["bin_start_um"].to_numpy() + economy.BIN_UM / 2
    for c in economy.CATEGORIES:
        pairs, counts = table[f"pairs_{c}"].to_numpy(), table[f"edges_{c}"].to_numpy()
        keep = pairs >= economy.MIN_PAIRS_PER_BIN
        probability = counts[keep] / pairs[keep]
        rho, p = stats.spearmanr(centres[keep], probability, alternative="less")
        within = centres[keep] <= economy.FIT_RANGE_UM
        fit = economy.exponential_fit(centres[keep][within], probability[within])
        d = s["distance_dependence"][c]
        assert d["bins"] == int(keep.sum()) and close([d["pairs"], d["edges"]], [pairs.sum(), counts.sum()]), c
        assert close([d["spearman_rho"], d["p_value"]], [rho, p]), f"{c}: distance correlation differs"
        assert close([d["a"], d["length_constant_um"]], [fit["a"], fit["length_constant_um"]], rel=1e-4), \
            f"{c}: exponential fit differs"
        assert d["significant"] == (p < economy.ALPHA), f"{c}: significance flag"
    assert close(s["probability_minima"], economy.probability_minima(table)), "probability minima differ"

    swaps = s["local_optimum"]
    assert close(swaps["start_cost"], placement["real"]), "swaps did not start from the real placement"
    assert close(swaps["reduction"], 1 - swaps["final_cost"] / swaps["start_cost"]), "swap reduction arithmetic"
    trajectory = np.array(swaps["trajectory"])
    assert trajectory[-1][0] == swaps["proposals"] == economy.N_SWAPS, "swap proposals differ from the protocol"
    assert (np.diff(trajectory[:, 1]) >= 0).all(), "cumulative swap saving decreases"
    assert close(trajectory[-1][1], swaps["reduction"], rel=1e-9), "trajectory does not end at the reported saving"
    assert swaps["supported"] == (swaps["reduction"] > 0.01), "H6 flag"

    shares = {row["label"]: row for row in s["cost_share"]["rows"]}
    total_cost = placement["real"]
    for label, key in (("neck-crossing", "crossing"), ("connective-incident", "incident")):
        row = shares[label]
        assert row["edges"] == value[key]["edges"], f"{label} edge count differs from connective_value.json"
        assert close(row["cost_share"] * total_cost, value[key]["cost_um"]), f"{label} cost differs"
        assert close(row["mean_length_um"], value[key]["mean_length_um"]), f"{label} mean length differs"
    for row in shares.values():
        assert close(row["edge_share"], row["edges"] / n_edges), f"{row['label']} edge share arithmetic"

    for label, test in s["compartment_optimality"].items():
        edges = table[f"edges_{'brain-brain' if label == 'brain' else 'vnc-vnc'}"].sum()
        assert test["edges"] == edges, f"{label} compartment edges differ from the distance table"
        assert close(test["p_value"], (1 + test["n_at_or_below_real"]) / (1 + test["n_permutations"])), label
        assert close([test["cost_ratio"], test["z_score"]],
                     [test["real"] / test["null_mean"], (test["real"] - test["null_mean"]) / test["null_sd"]]), label

    traffic = s["length_traffic"]
    assert traffic["edges_within_compartment"] == int(table["edges_brain-brain"].sum() + table["edges_vnc-vnc"].sum())
    price = result_json("connective_price.json")["tests"]
    assert traffic["connective_nodes_with_crossing_edges"] == price["descending"]["n"] + price["ascending"]["n"], \
        "connective nodes with crossing edges differ from the price analysis"

    expected = regenerated_report(economy, s)
    assert same_text(result_text("wiring_economy_extensions.md"), expected), "wiring_economy_extensions.md is out of date"
    return (f"distance fits and correlations reproduced from {len(table)} bins; swap saving "
            f"{100 * swaps['reduction']:.2f}%; cost shares match connective_value.json; report current")


if __name__ == "__main__":
    run(check)
