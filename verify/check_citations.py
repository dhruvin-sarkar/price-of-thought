"""Check every reference in the paper is one verified in the prior-art review, and every one is cited in the text."""

import re

from pipeline.common import ROOT
from verify.common import result_text, run

PAPER = ROOT / "paper" / "report.md"
IDENTIFIER = re.compile(r"(doi:\S+|arXiv:\S+)")
FIRST_AUTHOR = re.compile(r"^((?:van den )?[^\s,]+(?: y Cajal)?)")
# Books predate DOIs; every other reference carries one or an arXiv id.
WITHOUT_IDENTIFIER = ("Ramón y Cajal",)


def check() -> str:
    body, _, references = PAPER.read_text(encoding="utf-8").partition("\n# References\n")
    assert references, "the paper has no References section"
    entries = [line.strip() for line in references.strip().split("\n") if line.strip()]
    reviewed = result_text("prior_art.md").partition("## References")[2]
    verified = {line[2:].strip() for line in reviewed.split("\n") if line.startswith("- ")}

    missing = [e[:60] for e in entries if e not in verified]
    assert not missing, f"{len(missing)} references not in the verified prior-art list: {'; '.join(missing)}"
    uncited = []
    for entry in entries:
        author = FIRST_AUTHOR.match(entry).group(1)
        assert IDENTIFIER.search(entry) or author in WITHOUT_IDENTIFIER, f"no DOI or arXiv id: {entry[:60]}"
        year = re.search(r"\((\d{4})", entry).group(1)
        if not re.search(rf"{re.escape(author)}.{{0,40}}{year}", body):
            uncited.append(f"{author} {year}")
    assert not uncited, f"{len(uncited)} references never cited in the text: {', '.join(uncited)}"
    return f"{len(entries)} references, all among those verified in prior_art.md, each cited in the text"


if __name__ == "__main__":
    run(check)
