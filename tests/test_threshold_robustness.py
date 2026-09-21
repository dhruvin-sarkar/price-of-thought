import numpy as np
import pytest
from scipy import stats

from pipeline.threshold_robustness import hub_membership


def test_hub_membership_counts_and_direction():
    # Degrees 0 to 99 put the 90th percentile at 89.1, so ten nodes are high. Three of the five connective
    # nodes are among them, leaving seven of the other ninety-five.
    degree = np.arange(100)
    connective = np.zeros(100, dtype=bool)
    connective[[95, 96, 97, 5, 6]] = True
    result = hub_membership(degree, connective)

    assert result["degree_threshold"] == pytest.approx(89.1)
    assert result["connective_share_high"] == 3 / 5
    assert result["other_share_high"] == 7 / 95
    assert result["odds_ratio"] == pytest.approx(3 * 88 / (2 * 7))
    # One-sided Fisher on this table is the hypergeometric tail: three or more of the five connective nodes
    # among the ten highest-degree of a hundred.
    assert result["p_value"] == pytest.approx(stats.hypergeom.sf(2, 100, 10, 5))


def test_hub_membership_finds_nothing_when_the_connective_sits_at_the_bottom():
    degree = np.arange(100)
    connective = np.zeros(100, dtype=bool)
    connective[:5] = True
    result = hub_membership(degree, connective)

    assert result["connective_share_high"] == 0.0
    assert result["other_share_high"] == 10 / 95
    assert result["odds_ratio"] == 0.0
    assert result["p_value"] == 1.0
