"""Make the project's two typefaces available, from a local cache first and Google Fonts only when it is short."""

import re
from pathlib import Path

import requests
from fontTools.ttLib import TTFont
from matplotlib import font_manager

from pipeline.common import DATA

FONT_CACHE = DATA / "fonts"
CSS_URL = ("https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600&"
           "family=Spline+Sans+Mono:wght@400;500&display=swap")
SANS = "Archivo"
MONO = "Spline Sans Mono"
# Every family and weight the project sets text in, which is what CSS_URL asks the stylesheet for.
FACES = frozenset({(SANS, 400), (SANS, 500), (SANS, 600), (MONO, 400), (MONO, 500)})
SUFFIXES = (".ttf", ".otf")


class FontsUnavailable(Exception):
    """Raised when a typeface is neither in the cache nor reachable over the network."""


def face_of(path) -> tuple[str, int] | None:
    """The family and weight a font file carries, or None when it names neither of the project's families."""
    font = TTFont(path, lazy=True)
    name = font["name"].getDebugName(1) or ""
    family = MONO if name.startswith(MONO) else name.split(" ")[0]
    return (family, int(font["OS/2"].usWeightClass)) if family in (SANS, MONO) else None


def missing_faces(paths) -> set[tuple[str, int]]:
    """The families and weights the project needs that none of ``paths`` provides."""
    return set(FACES) - {face for face in (face_of(p) for p in paths) if face is not None}


def font_urls(user_agent: str = "Wget/1.20") -> list[str]:
    """Font file URLs from the Google Fonts stylesheet; the user agent decides the format served."""
    response = requests.get(CSS_URL, headers={"User-Agent": user_agent}, timeout=60)
    response.raise_for_status()
    return re.findall(r"url\((https://[^)]+)\)", response.text)


def cached_fonts(destination: Path | None = None) -> list[Path]:
    """Font files already in the cache, in name order, or an empty list when the directory is absent."""
    destination = destination or FONT_CACHE
    if not destination.is_dir():
        return []
    return sorted(p for p in destination.iterdir() if p.suffix.lower() in SUFFIXES)


def download_fonts(destination: Path | None = None, user_agent: str = "Wget/1.20") -> list[Path]:
    """Font files covering every face the project needs, from ``destination`` when it already holds them.

    Args:
        destination: the font cache directory; :data:`FONT_CACHE` when not given.
        user_agent: sent with the stylesheet request; it decides the file format Google Fonts serves.

    Returns:
        Paths to the font files, which together cover every entry of :data:`FACES`.

    Raises:
        FontsUnavailable: the cache is short of a face and Google Fonts cannot be reached.
        RuntimeError: the stylesheet was served but names no file for one of the faces, which would
            otherwise be substituted silently and change every glyph width.
    """
    destination = destination or FONT_CACHE
    have = cached_fonts(destination)
    if not missing_faces(have):
        return have

    destination.mkdir(parents=True, exist_ok=True)
    try:
        urls = font_urls(user_agent)
    except requests.RequestException as error:
        raise FontsUnavailable(f"{destination} is short of {sorted(missing_faces(have))} and the Google Fonts "
                               f"stylesheet could not be fetched: {error}") from error
    paths = []
    for url in urls:
        path = destination / url.rsplit("/", 1)[-1]
        if not path.exists():
            try:
                response = requests.get(url, timeout=120)
                response.raise_for_status()
            except requests.RequestException as error:
                raise FontsUnavailable(f"{url} could not be fetched into {destination}: {error}") from error
            path.write_bytes(response.content)
        paths.append(path)

    short = missing_faces(paths)
    if short:
        served = sorted({face for face in (face_of(p) for p in paths) if face is not None})
        raise RuntimeError(f"Google Fonts served no file for {sorted(short)}, only {served}; the project's "
                           "typefaces cannot be substituted without changing every glyph width")
    return paths


def register() -> tuple[str, str]:
    """Register the typefaces with matplotlib and return the (sans, mono) family names."""
    for path in download_fonts():
        font_manager.fontManager.addfont(str(path))
    available = {f.name for f in font_manager.fontManager.ttflist}
    missing = {SANS, MONO} - available
    if missing:
        raise RuntimeError(f"Typefaces not registered: {', '.join(sorted(missing))}")
    return SANS, MONO
