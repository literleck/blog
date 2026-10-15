"""Screenshot every page at 1200, 768 and 375 px into _screens/.

Usage: python3 tools/screens.py [site root]   The site root's folder must be named "blog".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `python3 tools/screens.py` finds the tools package
from tools import probe  # noqa: E402

WIDTHS = [1200, 768, 375]


def pages(root):
    posts = sorted(p.relative_to(root).as_posix() for p in (root / "posts").glob("[0-9][0-9][0-9]-*.html"))
    return ["index.html", "games.html", "about.html", "404.html"] + posts


def main(argv):
    root = Path(argv[1] if len(argv) > 1 else Path(__file__).resolve().parent.parent).resolve()
    out = root / "_screens"
    out.mkdir(exist_ok=True)
    for page in pages(root):
        for w in WIDTHS:
            target = out / f"{page.replace('/', '_').removesuffix('.html')}-{w}.png"
            probe.screenshot(root, page, w, 1400 if w > 500 else 1600, target)
            print(target.relative_to(root))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
