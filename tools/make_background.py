"""Generate the blog's background and favicon.

The background is a seamless "ghost overworld": an Ultima-style tile map of 8 x 8-pixel tiles,
drawn in white at low alpha, with the 7% overall strength baked in. The favicon is one water tile.

Usage: python3 tools/make_background.py   (writes assets/overworld.svg and assets/favicon.svg)
"""
import math
import random
from pathlib import Path

W, H = 40, 26          # map size in tiles; the SVG is 320 x 208 px and is drawn at 3x (960 x 624)
STRENGTH = 0.07        # overall opacity, baked into the SVG

# 8 x 8 pixel art. '.' is the tile's base; other characters are keys into the tile's palette.
TILES = {
    "grass":  ["........", "..a.....", "......a.", "........", "...a....", "........", ".a....a.", "........"],
    "grass2": ["........", "....a...", "........", ".a......", "......a.", "..a.....", "........", "....a..."],
    "tree":   ["...tt...", "..tTTt..", ".tTTTTt.", ".tTTTTt.", "..tTTt..", "...kk...", "...kk...", "........"],
    "forest": [".tt..tt.", "tTTttTTt", "tTTttTTt", ".tt..tt.", "..k..k..", "..k..k..", "........", "........"],
    "water":  ["........", ".ww.....", "...ww...", "........", "........", ".....ww.", "...ww...", "........"],
    "shore":  ["........", "..w.....", "........", "....w...", "........", ".w......", "........", "......w."],
    "mount":  ["........", "...Mm...", "..MMmn..", "..Mmmnn.", ".MMmmnn.", "MMmmmnnn", "Mmmmmnnn", "........"],
    "hill":   ["........", "........", "...hh...", "..hHHh..", ".hHHHHh.", "........", "..a.....", "........"],
    "path":   ["........", "..p.....", "......p.", "........", "....p...", ".p......", "........", "...p..p."],
}

# White at these opacities; None means transparent. Multiplied by STRENGTH on the page.
PALETTE = {
    "grass":  {".": None, "a": 0.25},
    "grass2": {".": None, "a": 0.25},
    "tree":   {".": None, "t": 0.33, "T": 0.45, "k": 0.25},
    "forest": {".": None, "t": 0.33, "T": 0.45, "k": 0.25},
    "water":  {".": 0.13, "w": 0.30},
    "shore":  {".": 0.08, "w": 0.20},
    "mount":  {".": None, "M": 0.60, "m": 0.40, "n": 0.25},
    "hill":   {".": None, "h": 0.30, "H": 0.40, "a": 0.25},
    "path":   {".": 0.12, "p": 0.25},
}

FAVICON = {"tile": "water", "colours": {".": "#2f5f78", "w": "#8fc0dc"}}


def noise(x, y, seed):
    """Smooth noise, periodic over the W x H map so the pattern tiles without seams."""
    rnd = random.Random(seed)
    v = 0.0
    for _ in range(7):
        fx, fy = rnd.randint(1, 3), rnd.randint(1, 3)
        px, py, a = rnd.random() * 2 * math.pi, rnd.random() * 2 * math.pi, rnd.random()
        v += a * math.sin(2 * math.pi * fx * x / W + px) * math.cos(2 * math.pi * fy * y / H + py)
    return v


def tile_at(x, y):
    e, f = noise(x, y, 7), noise(x, y, 99)
    j = random.Random(x * 131 + y * 17).random()
    if e < -0.55:
        return "water"
    if e < -0.35:
        return "shore"
    if e > 0.85 or (e > 0.65 and j < 0.6):
        return "mount"
    if e > 0.5 and j < 0.5:
        return "hill"
    if f > 0.25 and j < 0.85:
        return "forest" if f > 0.6 else "tree"
    if abs(f + 0.6) < 0.08:
        return "path"
    return "grass2" if j < 0.3 else "grass"


def _tile_group(name, colour_of):
    parts = []
    base = colour_of(".")
    if base:
        parts.append(f'<rect width="8" height="8" {base}/>')
    for y, row in enumerate(TILES[name]):
        for x, ch in enumerate(row):
            if ch != "." and colour_of(ch):
                parts.append(f'<rect x="{x}" y="{y}" width="1" height="1" {colour_of(ch)}/>')
    return "".join(parts)


def overworld_svg():
    defs = []
    for name in TILES:
        pal = PALETTE[name]
        defs.append(f'<g id="{name}">' + _tile_group(name, lambda ch: None if pal[ch] is None else f'fill="#fff" fill-opacity="{pal[ch]}"') + "</g>")
    uses = "".join(f'<use href="#{tile_at(x, y)}" x="{x * 8}" y="{y * 8}"/>' for y in range(H) for x in range(W))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * 8}" height="{H * 8}" viewBox="0 0 {W * 8} {H * 8}" shape-rendering="crispEdges">'
            f'<defs>{"".join(defs)}</defs><g opacity="{STRENGTH}">{uses}</g></svg>\n')


def favicon_svg():
    cols = FAVICON["colours"]
    body = _tile_group(FAVICON["tile"], lambda ch: f'fill="{cols[ch]}"')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8" shape-rendering="crispEdges">{body}</svg>\n'


def main():
    assets = Path(__file__).resolve().parent.parent / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "overworld.svg").write_text(overworld_svg(), encoding="utf-8")
    (assets / "favicon.svg").write_text(favicon_svg(), encoding="utf-8")
    print("wrote assets/overworld.svg and assets/favicon.svg")


if __name__ == "__main__":
    main()
