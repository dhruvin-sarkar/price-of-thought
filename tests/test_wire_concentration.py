import numpy as np
import pytest

from pipeline.wire_concentration import CURVE_POINTS, TOP_SHARES, lorenz, report, summary, tail


def power_law_sample(alpha: float, xmin: float, size: int, seed: int) -> np.ndarray:
    """Lengths drawn from a continuous power law with exponent ``alpha`` above ``xmin``."""
    uniform = np.random.default_rng(seed).random(size)
    return xmin * (1 - uniform) ** (-1 / (alpha - 1))


def test_equal_lengths_give_a_gini_of_zero_and_a_curve_on_the_diagonal():
    curve = lorenz(np.full(500, 7.0))
    assert curve["gini"] == 0.0
    assert curve["wire_share"] == pytest.approx(curve["connection_share"], abs=1e-6)
    assert curve["connections"] == 500


def test_one_length_holding_the_whole_budget_pushes_the_gini_to_one():
    curve = lorenz(np.concatenate([[1e6], np.ones(999)]))
    assert curve["gini"] > 0.99
    assert curve["top_shares"]["0.001"] > 0.99


def test_the_curve_rises_to_the_whole_budget_and_stays_above_equality():
    curve = lorenz(np.random.default_rng(7).lognormal(3.0, 1.0, size=4000))
    assert len(curve["connection_share"]) == len(curve["wire_share"]) <= CURVE_POINTS
    assert curve["wire_share"] == sorted(curve["wire_share"])
    assert curve["wire_share"][-1] == pytest.approx(1.0)
    assert curve["connection_share"][-1] == pytest.approx(1.0)
    assert all(w >= c - 1e-6 for c, w in zip(curve["connection_share"], curve["wire_share"]))
    assert set(curve["top_shares"]) == {f"{s:g}" for s in TOP_SHARES}


def test_top_shares_hold_the_wire_of_the_longest_connections():
    # Ten connections of 9 um and ninety of 1 um: 180 um in all, half of it in the longest tenth.
    curve = lorenz(np.concatenate([np.full(10, 9.0), np.ones(90)]))
    held = curve["top_shares"]
    assert held["0.01"] == pytest.approx(9 / 180, abs=5e-5)
    assert held["0.05"] == pytest.approx(45 / 180, abs=5e-5)
    assert held["0.1"] == pytest.approx(0.5, abs=5e-5)
    assert held["0.25"] == pytest.approx(105 / 180, abs=5e-5)
    assert held["0.5"] == pytest.approx(130 / 180, abs=5e-5)


def test_summary_reports_the_count_total_and_upper_quantiles():
    assert summary(np.arange(1, 101, dtype=float)) == {
        "edges": 100, "wire_um": 5050.0, "mean_um": 50.5, "median_um": 50.5,
        "p90_um": 90.1, "p99_um": 99.01, "max_um": 100.0,
    }


def test_tail_recovers_the_exponent_of_a_power_law_sample():
    fit = tail(power_law_sample(alpha=2.5, xmin=60.0, size=2000, seed=1))
    assert fit["alpha"] == pytest.approx(2.5, abs=0.3)
    assert fit["xmin_um"] >= 1
    assert 0 < fit["tail_edges"] <= 2000
    assert set(fit["comparisons"]) == {"lognormal", "exponential", "truncated_power_law"}
    for comparison in fit["comparisons"].values():
        assert np.isfinite(comparison["loglikelihood_ratio"])
        assert 0 <= comparison["p_value"] <= 1


def test_report_states_the_headline_numbers_it_was_given():
    lengths = np.concatenate([np.full(900, 10.0), np.full(100, 1000.0)])
    result = {
        "lengths": {"all": summary(lengths)},
        "lorenz": {"all": lorenz(lengths)},
        "tail": {"xmin_um": 250.0, "alpha": 2.4, "tail_edges": 100,
                 "comparisons": {"lognormal": {"loglikelihood_ratio": 1.2, "p_value": 0.03}}},
        "superclasses": [{"superclass": "central", "types": 40, "edges": 1000, "wire_um": 109000.0,
                          "wire_share": 1.0, "mean_length_um": 109.0, "median_length_um": 10.0}],
        "total_wire_um": 109000.0,
    }
    curve = result["lorenz"]["all"]
    text = report(result)
    assert "1,000 connections" in text
    assert "0.11 m of wire" in text
    assert f"the top 1% hold {curve['top_shares']['0.01'] * 100:.1f}%" in text
    assert f"the top 10% hold {curve['top_shares']['0.1'] * 100:.1f}%" in text
    assert f"coefficient of the length distribution is {curve['gini']:.3f}" in text
    assert "above 250" in text and "exponent 2.40" in text
    assert "| central |" in text and "| lognormal |" in text
