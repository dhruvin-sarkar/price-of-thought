import re

from pipeline.common import RESULTS, ROOT

METHODS = ROOT / "web" / "src" / "components" / "Methods.jsx"


def site_references() -> list[str]:
    """The reference strings the site's methods section lists."""
    block = METHODS.read_text(encoding="utf-8").partition("const REFERENCES = [")[2].partition("];")[0]
    return re.findall(r'"((?:[^"\\]|\\.)*)"', block)


def test_the_site_lists_the_prior_work_the_report_builds_on():
    assert len(site_references()) >= 8


def test_every_reference_the_site_cites_is_one_verified_in_the_prior_art_review():
    reviewed = (RESULTS / "prior_art.md").read_text(encoding="utf-8").partition("## References")[2]
    for reference in site_references():
        doi = re.search(r"doi:(\S+)", reference).group(1)
        assert doi in reviewed, doi


INDEX = ROOT / "web" / "index.html"
SITE = "https://dhruvin-sarkar.github.io/price-of-thought/"
# Paths the build produces rather than copies: the page itself, and the report the Vite plugin publishes.
BUILT = {"": ROOT / "web" / "index.html", "report.pdf": ROOT / "paper" / "report.pdf"}


def test_every_asset_the_page_metadata_points_at_is_published():
    for url in set(re.findall(rf'content="{re.escape(SITE)}([^"]*)"', INDEX.read_text(encoding="utf-8"))):
        path = BUILT.get(url, ROOT / "web" / "public" / url)
        assert path.exists(), url
