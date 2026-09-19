"""Check every README figure is committed, well formed, and describes the numbers in the current results."""

import xml.etree.ElementTree as ET

from pipeline import readme_assets as ra
from verify.common import run

NS = "{http://www.w3.org/2000/svg}"


def check() -> str:
    data = ra.load_inputs()
    jobs = [ra.title_plate(data)] + [build(data, theme) for build in ra.THEMED for theme in ra.THEMES]
    for _, desc, name in jobs:
        path = ra.OUT_DIR / name
        assert path.exists(), f"assets/readme/{name} is missing; run make readme"
        committed = ET.fromstring(path.read_text(encoding="utf-8")).find(f"{NS}desc").text
        assert committed == desc, f"assets/readme/{name} describes different numbers than the results; run make readme"
    return f"{len(jobs)} README figures match the results"


if __name__ == "__main__":
    run(check)
