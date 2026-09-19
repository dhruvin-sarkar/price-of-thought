"""Check every placement-test statistic is reproduced by the saved permutation costs and matches the report."""

import numpy as np

from pipeline.spatial_permutation_test import ALPHA, N_PERMUTATIONS, VARIANTS, summarize
from verify.common import close, result_csv, result_json, result_text, run

# spatial_permutation_costs.csv is written with six significant digits, about 500 µm on a 2e8 µm cost. That moves the
# mean, extremes and ratio by under 1e-5 but the standard deviation, about 4e5 µm, and so the z-score, by up to ~0.3%.
REL = {"null_sd": 5e-3, "z_score": 5e-3}
DEFAULT_REL = 1e-5


def check() -> str:
    summary = result_json("spatial_optimality.json")
    costs = result_csv("spatial_permutation_costs.csv")
    report = result_text("spatial_optimality.md")
    assert summary["alpha"] == ALPHA, f"alpha {summary['alpha']}"
    assert set(summary["analyses"]) == set(VARIANTS), f"analyses {sorted(summary['analyses'])}"
    assert len(costs) == N_PERMUTATIONS and (costs["permutation"] == np.arange(N_PERMUTATIONS)).all(), \
        "permutation table is not 0 .. N-1"
    assert close(summary["analyses"]["primary"]["real"], summary["analyses"]["within_compartment"]["real"], rel=0), \
        "the within-compartment test is not on the primary graph and positions"

    for key, label in VARIANTS.items():
        s = summary["analyses"][key]
        expected = summarize(s["real"], costs[key].to_numpy())
        for field, value in expected.items():
            assert close(s[field], value, rel=REL.get(field, DEFAULT_REL)), \
                f"{key} {field}: {s[field]} recorded, {value} from the costs"
        assert s["p_value"] >= 1 / (N_PERMUTATIONS + 1), f"{key}: p below the attainable floor"
        row = (f"| {s['n_at_or_below_real']} / {s['n_permutations']} | {s['z_score']:.1f} | {s['cost_ratio']:.3f} | "
               f"{s['p_value']:.4f} | {'yes' if s['significant'] else 'no'} |")
        assert f"| {label} |" in report and row in report, f"spatial_optimality.md row for {key} differs"

    primary = summary["analyses"]["primary"]
    verdict = "H is supported" if primary["significant"] and primary["real"] < primary["null_mean"] else \
        "H is not supported"
    assert f"{verdict}." in report, f"spatial_optimality.md verdict should read '{verdict}'"
    return (f"{len(VARIANTS)} analyses reproduced from {N_PERMUTATIONS} saved permutations; primary ratio "
            f"{primary['cost_ratio']:.3f}, z = {primary['z_score']:.1f}; report rows and verdict current")


if __name__ == "__main__":
    run(check)
