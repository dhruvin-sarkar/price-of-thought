"""Check the hero image exists at the required resolution."""

from PIL import Image

from pipeline.common import ASSETS
from verify.common import run

MIN_SIZE = (1920, 1080)


def check() -> str:
    path = ASSETS / "hero.png"
    assert path.exists(), "assets/hero.png is missing"
    with Image.open(path) as image:
        size, mode = image.size, image.mode
    assert size[0] >= MIN_SIZE[0] and size[1] >= MIN_SIZE[1], f"hero.png is {size[0]}x{size[1]}, below {MIN_SIZE}"
    return f"assets/hero.png is {size[0]}x{size[1]} ({mode})"


if __name__ == "__main__":
    run(check)
