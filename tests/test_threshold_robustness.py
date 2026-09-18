import numpy as np

from pipeline.threshold_robustness import hub_membership


def test_hub_membership_counts_and_direction():
    degree = np.arange(100)
    connective = np.zeros(100, dtype=bool)
    connective[[95, 96, 97, 5, 6]] = True
    result = hub_membership(degree, connective)
    high = degree >= np.quantile(degree, 0.9)
    assert result["degree_threshold"] == np.quantile(degree, 0.9)
    assert result["connective_share_high"] == 3 / 5
    assert result["other_share_high"] == (high.sum() - 3) / 95
    assert result["odds_ratio"] > 1 and result["p_value"] < 0.05
