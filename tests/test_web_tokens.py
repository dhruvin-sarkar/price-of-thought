import re

from pipeline.common import ROOT
from pipeline.readme_assets import THEMES

TOKENS = ROOT / "web" / "src" / "styles" / "tokens.css"

# The custom property each colour of a committed figure is published under on the site.
NAMES = {
    "ground": "paper",
    "plate": "paper-raised",
    "track": "wash",
    "rule": "rule",
    "rule_strong": "rule-strong",
    "ink": "ink",
    "ink2": "ink-2",
    "ink3": "ink-3",
    "axis": "axis",
    "wire": "wire",
    "wire_ink": "wire-ink",
    "null": "null",
}

SELECTORS = {"light": ":root", "dark": ':root[data-theme="dark"]'}


def declarations(selector: str) -> dict[str, str]:
    """Custom properties declared by this selector, merged across every rule that uses it."""
    css = TOKENS.read_text(encoding="utf-8")
    out = {}
    for block in re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css):
        out.update(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", block))
    return out


def test_each_theme_publishes_the_palette_of_the_committed_figures():
    for theme, palette in THEMES.items():
        declared = declarations(SELECTORS[theme])
        for key, name in NAMES.items():
            assert declared[name] == palette[key], f"{theme} {name}"
        for i, stop in enumerate(palette["ramp"]):
            assert declared[f"ramp-{i}"] == stop, f"{theme} ramp-{i}"


def test_the_black_field_matches_the_dark_theme_it_is_taken_from():
    field = declarations(":root")
    dark = THEMES["dark"]
    pairs = (("ground", "field"), ("plate", "field-raised"), ("rule", "field-rule"), ("ink", "field-ink"),
             ("ink2", "field-ink-2"), ("ink3", "field-ink-3"), ("wire", "field-wire"),
             ("wire_ink", "field-wire-ink"), ("null", "field-null"))
    for key, name in pairs:
        assert field[name] == dark[key], name


def test_every_colour_is_written_as_a_six_digit_hex():
    for selector in (*SELECTORS.values(), ":root"):
        for name, value in declarations(selector).items():
            if value.startswith("#"):
                assert re.fullmatch(r"#[0-9a-f]{6}", value), f"{name}: {value}"
