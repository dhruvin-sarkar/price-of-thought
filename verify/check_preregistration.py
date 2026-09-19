"""Check every hypothesis section is unchanged since its pre-registration commit, which predates its results."""

import subprocess

from pipeline.common import ROOT
from verify.common import git_show, result_json, result_text, run

# report, pre-registration commit, result files first committed after it, JSON recording the commit
REGISTRATIONS = [
    ("spatial_optimality.md", "39892c5", ["spatial_optimality.json"], "spatial_optimality.json"),
    ("connective_richclub.md", "e62c6df", ["connective_richclub.json"], "connective_richclub.json"),
    ("connective_value.md", "e62c6df", ["connective_value.json"], "connective_value.json"),
    ("wiring_economy_extensions.md", "e62c6df", ["wiring_economy_extensions.json", "cable_length.json"],
     "wiring_economy_extensions.json"),
    ("generative_model.md", "e62c6df", ["generative_model.json", "generative_comparison.json"], "generative_model.json"),
    ("connective_price.md", "73fba33", ["connective_price.json"], "connective_price.json"),
    ("threshold_robustness.md", "73fba33", ["threshold_robustness.json"], "threshold_robustness.json"),
]


def lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.replace("\r\n", "\n").strip().split("\n")]


def first_commit(path: str) -> str:
    added = subprocess.run(["git", "log", "--diff-filter=A", "--format=%H", "--", path], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.split()
    assert added, f"{path} was never committed"
    return added[-1]


def strictly_before(early: str, late: str) -> bool:
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", early, late], cwd=ROOT).returncode == 0
    resolved = subprocess.run(["git", "rev-parse", early, late], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.split()
    return ancestor and resolved[0] != resolved[1]


def check() -> str:
    for report, commit, outputs, recorded in REGISTRATIONS:
        registered = lines(git_show(commit, f"results/{report}"))
        current = lines(result_text(report))
        assert current[:len(registered)] == registered, \
            f"{report}: the hypothesis section differs from its pre-registration in {commit}"
        assert result_json(recorded)["preregistration_commit"] == commit, \
            f"{recorded} records a different pre-registration commit"
        for output in outputs:
            assert strictly_before(commit, first_commit(f"results/{output}")), \
                f"results/{output} was first committed before or with its pre-registration {commit}"
    return (f"{len(REGISTRATIONS)} hypothesis sections unchanged since pre-registration, each committed before its "
            f"results")


if __name__ == "__main__":
    run(check)
