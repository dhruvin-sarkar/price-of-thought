"""Check the removal curves, the matching between the three schedules and the report against the saved result."""

import pipeline.length_tradeoff as length_tradeoff
from pipeline.length_tradeoff import LONGEST, RANDOM, SHORTEST
from verify.common import close, result_json, result_text, run, same_text


def check() -> str:
    s = result_json("length_tradeoff.json")
    graph, sampling, baseline, curves = s["graph"], s["sampling"], s["baseline"], s["curves"]
    comparison = s["comparison"]

    assert sampling["wire_fractions"] == list(length_tradeoff.WIRE_FRACTIONS), "the curve was sampled elsewhere"
    assert sampling["points"] == len(sampling["wire_fractions"])
    assert sampling["sources"] == length_tradeoff.N_SOURCES
    assert sampling["random_repeats"] == length_tradeoff.N_RANDOM
    assert set(curves) == {LONGEST, RANDOM, SHORTEST}, "a schedule is missing"
    assert baseline == {k: curves[LONGEST][0][k] for k in baseline}, "the baseline is not the first point measured"
    assert baseline["largest_component"] <= graph["nodes"], "the component holds more nodes than the graph has"

    longest_curve = curves[LONGEST]
    for name, rows in curves.items():
        assert len(rows) == sampling["points"], f"the {name} curve has the wrong number of points"
        first = rows[0]
        assert first["edges_removed"] == 0 and first["wire_removed_um"] == 0, f"the {name} curve starts part way in"
        assert close(first["efficiency_share"], 1.0, rel=1e-6), f"the {name} curve is not scaled to its own start"
        assert close(first["efficiency"], baseline["efficiency"], rel=1e-6), f"the {name} curve starts elsewhere"
        for row in rows:
            assert close(row["edges_removed_share"], row["edges_removed"] / graph["edges"], rel=1e-3, abs_tol=1e-5)
            assert close(row["wire_removed_share"], row["wire_removed_um"] / graph["total_wire_um"],
                         rel=1e-3, abs_tol=1e-5), f"{name} wire share"
            assert close(row["largest_component_share"], row["largest_component"] / graph["nodes"],
                         rel=1e-4), f"{name} component share"
            assert close(row["efficiency_share"], row["efficiency"] / baseline["efficiency"],
                         rel=1e-3, abs_tol=1e-5), f"{name} efficiency share"
        # Removal only ever takes more away, and neither measure can rise as it does.
        for before, after in zip(rows, rows[1:]):
            assert before["edges_removed"] < after["edges_removed"], f"the {name} curve stops removing"
            assert before["wire_removed_um"] < after["wire_removed_um"], f"the {name} curve stops removing wire"
            assert before["efficiency"] >= after["efficiency"], f"the {name} curve gains efficiency"
            assert before["largest_component"] >= after["largest_component"], f"the {name} component grows"

    for fraction, row in zip(sampling["wire_fractions"], longest_curve):
        assert row["wire_removed_share"] >= fraction - 1e-5, "the longest-first schedule undershoots its target"
    for fraction, long_row, short_row, random_row in zip(sampling["wire_fractions"], longest_curve,
                                                         curves[SHORTEST], curves[RANDOM]):
        assert short_row["wire_removed_share"] >= fraction - 1e-5, "the shortest-first schedule undershoots"
        # The two ends are matched on wire, so the short end has to take more connections to get there.
        assert close(long_row["wire_removed_share"], short_row["wire_removed_share"], rel=1e-2, abs_tol=1e-4), \
            f"the two ends are not matched on wire at {fraction:g}"
        assert short_row["edges_removed"] >= long_row["edges_removed"], \
            f"the short end takes fewer connections than the long end at {fraction:g}"
        # Random is matched on the count instead, and its connections are shorter than the longest.
        assert random_row["edges_removed"] == long_row["edges_removed"], \
            f"the random schedule is not matched on count at {fraction:g}"
        assert random_row["wire_removed_um"] <= long_row["wire_removed_um"] + 1, \
            f"random removal took more wire than taking the longest at {fraction:g}"
        assert random_row["efficiency_share_sd"] >= 0, "a negative spread over the random draws"

    reference = sampling["wire_fractions"].index(comparison["reference_wire_fraction"])
    for name, row in comparison["at_reference"].items():
        assert row == curves[name][reference], f"the {name} reference point is not the point measured"
        lost = comparison["efficiency_lost_per_metre"][name]
        assert close(lost, (1 - row["efficiency_share"]) / (row["wire_removed_um"] / 1e6), rel=1e-3), \
            f"{name} efficiency lost per metre"
        assert lost > 0, f"{name} lost no efficiency at the reference point"

    for name, share in comparison["wire_share_to_halve_efficiency"].items():
        reached = min(row["efficiency_share"] for row in curves[name])
        if share is None:
            assert reached > length_tradeoff.HALF, f"the {name} curve does halve but no crossing was recorded"
        else:
            assert reached <= length_tradeoff.HALF, f"the {name} curve never halves but a crossing was recorded"
            assert 0 < share <= curves[name][-1]["wire_removed_share"], f"{name} crossing is off the curve"
    half = comparison["wire_share_to_halve_efficiency"]
    both_halve = half[LONGEST] is not None and half[SHORTEST] is not None
    assert ("halving_wire_ratio" in comparison) == both_halve, \
        "the halving ratio is recorded exactly when both ends do halve efficiency"
    if both_halve:
        assert close(comparison["halving_wire_ratio"], half[LONGEST] / half[SHORTEST], rel=1e-3), "halving ratio"

    assert same_text(result_text("length_tradeoff.md"), length_tradeoff.report(s)), "length_tradeoff.md is out of date"
    at = comparison["at_reference"]
    lost = comparison["efficiency_lost_per_metre"]
    return (f"{sampling['points']} points over {graph['edges']:,} connections; removing "
            f"{comparison['reference_wire_fraction'] * 100:.0f}% of the wire leaves efficiency at "
            f"{at[LONGEST]['efficiency_share'] * 100:.1f}% from the long end against "
            f"{at[SHORTEST]['efficiency_share'] * 100:.1f}% from the short, "
            f"{lost[SHORTEST] / lost[LONGEST]:.1f} times the cost per metre; report current")


if __name__ == "__main__":
    run(check)
