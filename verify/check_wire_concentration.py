"""Check the Lorenz curves, the tail fit, the per-superclass budget and the report against the saved result."""

import pipeline.wire_concentration as wire_concentration
from verify.common import close, result_json, result_text, run, same_text


def check() -> str:
    s = result_json("wire_concentration.json")
    lengths, curves, rows = s["lengths"], s["lorenz"], s["superclasses"]

    whole = lengths["all"]
    assert close(whole["wire_um"], s["total_wire_um"], rel=1e-6), "the total wire disagrees with the whole-set summary"
    assert close(whole["mean_um"], whole["wire_um"] / whole["edges"], rel=1e-3), "mean length arithmetic"
    # The three groups are views, not a partition. A brain-to-nerve-cord connection between two types that are
    # neither descending nor ascending sits outside all three, and a descending or ascending type whose own
    # compartment label is on the far side from its class puts a neck-crossing connection inside one of the
    # other two as well. Only the two within-compartment groups are disjoint by construction.
    for name in ("within the brain", "within the nerve cord", "across the neck"):
        assert 0 < lengths[name]["edges"] <= whole["edges"], f"{name} holds an impossible number of connections"
        assert 0 < lengths[name]["wire_um"] <= whole["wire_um"], f"{name} holds an impossible amount of wire"
    sides = ("within the brain", "within the nerve cord")
    assert sum(lengths[p]["edges"] for p in sides) <= whole["edges"], "the two sides overlap"
    assert sum(lengths[p]["wire_um"] for p in sides) <= whole["wire_um"] + 1, "the two sides overlap"
    for name, group in lengths.items():
        assert group["median_um"] <= group["p90_um"] <= group["p99_um"] <= group["max_um"], \
            f"{name} quantiles are out of order"

    for name, curve in curves.items():
        assert curve["connections"] == lengths[name]["edges"], f"{name} curve covers a different set"
        assert len(curve["connection_share"]) == len(curve["wire_share"]) <= wire_concentration.CURVE_POINTS, \
            f"{name} curve is the wrong length"
        assert close(curve["wire_share"][-1], 1.0, rel=1e-3), f"{name} curve does not reach the whole budget"
        # Longest first, so the curve rises and always sits above the diagonal it is measured against.
        assert all(a <= b for a, b in zip(curve["wire_share"], curve["wire_share"][1:])), f"{name} curve falls"
        assert all(w >= c - 1e-6 for c, w in zip(curve["connection_share"], curve["wire_share"])), \
            f"{name} curve dips below equality"
        assert 0 <= curve["gini"] < 1, f"{name} Gini out of range"
        assert set(curve["top_shares"]) == {f"{s:g}" for s in wire_concentration.TOP_SHARES}, \
            f"{name} top shares cover other fractions"
        held = [curve["top_shares"][f"{s:g}"] for s in sorted(wire_concentration.TOP_SHARES)]
        assert all(a <= b for a, b in zip(held, held[1:])), f"{name} top shares are not increasing"

    t = s["tail"]
    assert t["alpha"] > 1, "a power law needs an exponent above one to normalize"
    assert 0 < t["tail_edges"] <= whole["edges"], "the fitted tail holds more connections than there are"
    assert t["xmin_um"] <= whole["max_um"], "the fitted lower bound is above the longest connection"
    assert set(t["comparisons"]) == {"lognormal", "exponential", "truncated_power_law"}, \
        "the tail is weighed against other alternatives"
    beaten = [n for n, c in t["comparisons"].items() if c["loglikelihood_ratio"] > 0 and c["p_value"] < 0.05]
    lost = [n for n, c in t["comparisons"].items() if c["loglikelihood_ratio"] < 0 and c["p_value"] < 0.05]
    undecided = sorted(set(t["comparisons"]) - set(beaten) - set(lost))
    assert not undecided, f"the tail fit is neither better nor worse than {', '.join(undecided)}"

    assert close(sum(r["wire_share"] for r in rows), sum(r["wire_um"] for r in rows) / s["total_wire_um"], rel=1e-3), \
        "the superclass shares do not match their wire"
    assert [r["wire_um"] for r in rows] == sorted((r["wire_um"] for r in rows), reverse=True), \
        "the superclasses are not ordered by the wire they own"
    for row in rows:
        # A connection is counted for both classes it touches, so the shares may add to more than one.
        assert row["wire_share"] <= 1 + 1e-9, f"{row['superclass']} owns more than the whole budget"
        assert close(row["mean_length_um"], row["wire_um"] / row["edges"], rel=1e-3), \
            f"{row['superclass']} mean length arithmetic"

    assert same_text(result_text("wire_concentration.md"), wire_concentration.report(s)), \
        "wire_concentration.md is out of date"
    return (f"Gini {curves['all']['gini']:.3f} over {whole['edges']} connections, tail exponent {t['alpha']:.2f} "
            f"above {t['xmin_um']:g} um beating {len(beaten)} and losing to {len(lost)} of three alternatives; "
            f"{len(rows)} superclass budgets and the report current")


if __name__ == "__main__":
    run(check)
