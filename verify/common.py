"""Shared helpers for the result checks: strict JSON loading, tolerant comparison, report regeneration and a runner."""

import json
import math
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pandas as pd

from pipeline.build_spatial_graph import NODES_PATH
from pipeline.common import RESULTS, ROOT


class Skip(Exception):
    """Raised by a check whose inputs are legitimately absent."""


def reject_constant(name: str):
    raise ValueError(f"non-finite value {name}")


def read_json(path: Path):
    """Parse a JSON file, failing on NaN or Infinity."""
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def result_json(name: str):
    return read_json(RESULTS / name)


def result_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


def result_text(name: str) -> str:
    return (RESULTS / name).read_text(encoding="utf-8")


def data_available() -> bool:
    """Whether the local neuPrint cache the graph is built from is on disk."""
    return NODES_PATH.exists()


def close(a, b, rel: float = 1e-6, abs_tol: float = 1e-9) -> bool:
    """Tolerant equality for numbers, None and nested lists or dicts of them."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], rel, abs_tol) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(close(x, y, rel, abs_tol) for x, y in zip(a, b))
    if a is None or b is None or isinstance(a, (str, bool)) or isinstance(b, (str, bool)):
        return a == b
    return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=abs_tol)


def same_text(actual: str, expected: str) -> bool:
    """Equality of two documents up to line endings and trailing whitespace."""
    def normalize(text: str) -> str:
        return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").strip().split("\n"))

    return normalize(actual) == normalize(expected)


def regenerated_report(module: ModuleType, *args, report: Path | None = None) -> str:
    """Text that ``module.write_report(*args)`` produces from a copy of the committed report.

    Parameters: ``module`` has a ``REPORT`` path and a ``write_report`` that reads its hypothesis section from
    ``REPORT``; ``report`` replaces the file copied, for a report that another module extends.
    Returns the regenerated text; the committed file is not touched.
    """
    committed = module.REPORT
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / committed.name
        shutil.copyfile(report or committed, path)
        module.REPORT = path
        try:
            module.write_report(*args)
        finally:
            module.REPORT = committed
        return path.read_text(encoding="utf-8")


def git_show(commit: str, path: str) -> str:
    """Contents of ``path`` at ``commit``; raises :class:`Skip` when that commit is not in a shallow history."""
    known = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, capture_output=True)
    if known.returncode != 0:
        raise Skip(f"commit {commit} is not in the local history")
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True)
    assert result.returncode == 0, f"{path} does not exist at {commit}"
    return result.stdout.decode("utf-8")


def run(check: Callable[[], str]) -> None:
    """Run ``check``, print one OK, SKIP or FAIL line, and exit non-zero on failure.

    Parameters: ``check`` returns a one-line summary on success, raises :class:`Skip` when its inputs are
    absent, and raises any other exception on failure.
    """
    try:
        summary = check()
    except Skip as skip:
        print(f"SKIP: {skip}")
        return
    except AssertionError as error:
        print(f"FAIL: {error}")
        sys.exit(1)
    except Exception as error:  # noqa: BLE001
        print(f"FAIL: {type(error).__name__}: {error}")
        sys.exit(1)
    print(f"OK: {summary}")
