"""Check that every file the README, the paper and the result reports point to exists in the repository."""

import re
from pathlib import Path

from pipeline.common import RESULTS, ROOT
from verify.common import run

LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")
CODE_PATH = re.compile(r"`((?:results|pipeline|export|verify|tests|assets|paper)/[^`\s]+)`")
HTML_PATH = re.compile(r'(?:src|srcset|href)="([^"#]+)"')


def documents() -> list[Path]:
    return [p for p in [ROOT / "README.md", ROOT / "paper" / "report.md", *sorted(RESULTS.glob("*.md"))] if p.exists()]


def check() -> str:
    broken, checked = [], 0
    for doc in documents():
        text = doc.read_text(encoding="utf-8")
        links = LINK.findall(text) + HTML_PATH.findall(text)
        targets = [doc.parent / m for m in links if not re.match(r"^[a-z]+:", m)]
        targets += [ROOT / m.rstrip(".,;:") for m in CODE_PATH.findall(text)]
        for target in targets:
            checked += 1
            if not target.resolve().exists():
                broken.append(f"{doc.relative_to(ROOT).as_posix()} -> {target.resolve().relative_to(ROOT).as_posix()}")
    assert not broken, f"{len(broken)} broken references: {'; '.join(sorted(set(broken)))}"
    assert checked, "no document pointed at a file, so nothing was resolved"
    return f"{checked} file references in {len(documents())} documents all resolve"


if __name__ == "__main__":
    run(check)
