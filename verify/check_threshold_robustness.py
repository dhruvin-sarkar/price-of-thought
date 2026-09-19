"""Check the threshold robustness test: the 1% row reproduces the original analyses, flags follow the statistics."""

import pipeline.threshold_robustness as robustness
from verify.common import close, regenerated_report, result_json, result_text, run, same_text


def check() -> str:
    s = result_json("threshold_robustness.json")
    rows = {r["fraction"]: r for r in s["thresholds"]}
    assert tuple(rows) == robustness.FRACTIONS, f"thresholds {tuple(rows)}"
    assert (s["n_permutations"], s["n_nulls"]) == (robustness.N_PERMUTATIONS, robustness.N_NULLS)

    original = rows[0.01]
    graph = result_json("spatial_graph_summary.json")["spatial_graph"]
    assert (original["nodes"], original["edges"]) == (graph["nodes"], graph["edges"]), "1% graph differs"
    placement = result_json("spatial_optimality.json")["analyses"]["primary"]
    assert close(original["placement"], placement), "1% placement test does not reproduce spatial_optimality.json"
    richclub = result_json("connective_richclub.json")
    assert original["layer_edges"] == richclub["layer_edges"], "1% layers differ from connective_richclub.json"
    assert close(original["routes"], richclub["routes_top10"]), "1% routes do not reproduce connective_richclub.json"
    membership = richclub["whole_cns_membership"]
    assert close([original["hubs"]["odds_ratio"], original["hubs"]["p_value"]],
                 [membership["odds_ratio"], membership["p_value"]]), "1% hub test differs"

    edges = [rows[f]["edges"] for f in robustness.FRACTIONS]
    assert edges == sorted(edges, reverse=True), "edge count does not fall as the threshold rises"
    for fraction, r in rows.items():
        assert r["nodes"] == graph["nodes"], f"{fraction}: node set changed"
        p, routes, hubs = r["placement"], r["routes"]["total"], r["hubs"]
        holds = {
            "placement": p["n_at_or_below_real"] == 0 and p["p_value"] < robustness.ALPHA,
            "routes": routes["ratio"] > 1 and routes["p_value"] < robustness.ALPHA,
            "hubs": hubs["odds_ratio"] > 1 and hubs["p_value"] < robustness.ALPHA,
        }
        assert r["holds"] == holds, f"{fraction}: flags {r['holds']} do not follow the statistics {holds}"
    tested = [r for f, r in rows.items() if f != 0.01]
    assert s["h11_supported"] == all(all(r["holds"].values()) for r in tested), "H11 flag"

    expected = regenerated_report(robustness, s)
    assert same_text(result_text("threshold_robustness.md"), expected), "threshold_robustness.md is out of date"
    failing = [f"{t} at {100 * f:g}%" for f, r in rows.items() for t, ok in r["holds"].items() if not ok]
    return (f"1% row reproduces the placement, route and hub analyses; flags follow the statistics; "
            f"H11 {'supported' if s['h11_supported'] else 'not supported'} ({', '.join(failing) or 'none failing'}); "
            f"report current")


if __name__ == "__main__":
    run(check)
