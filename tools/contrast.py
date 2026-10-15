"""WCAG contrast check for the blog's colour tokens (design spec §5.3).

Usage: python3 tools/contrast.py [path/to/styles.css]
Exit status 0 when every pair meets its threshold, 1 otherwise.
"""
import re
import sys
from pathlib import Path

# (foreground token, background token, minimum ratio, where the pair appears)
PAIRS = [
    ("head", "bg", 4.5, "name and current menu item on the background"),
    ("head2", "bg", 4.5, "tagline, menu, links and previous/next on the background"),
    ("cursor", "bg", 3.0, "the ▸ mark and the focus outline on the background"),
    ("title", "paper", 4.5, "titles"),
    ("text", "paper", 4.5, "body text"),
    ("muted", "paper", 4.5, "summaries and captions"),
    ("rust", "paper", 4.5, "links, the quest label and the ▼"),
    ("tab-fg", "tab-bg", 4.5, "date tabs"),
    ("text", "code-inline", 4.5, "inline code"),
    ("code-fg", "code-bg", 4.5, "code block text"),
    ("hl-comment", "code-bg", 4.5, "code comments"),
    ("hl-keyword", "code-bg", 4.5, "code keywords"),
    ("hl-function", "code-bg", 4.5, "code function names"),
]


def _channel(v):
    v = v / 255
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def luminance(colour):
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def read_tokens(css):
    """The opaque colour tokens (#rrggbb) declared in the first :root block, lower-cased."""
    m = re.search(r":root\s*\{(.*?)\}", css, re.S)
    if not m:
        return {}
    return {k: v.lower() for k, v in re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", m.group(1))}


def check(tokens):
    problems = []
    for fg, bg, minimum, where in PAIRS:
        if fg not in tokens or bg not in tokens:
            problems.append(f"missing token --{fg} or --{bg} ({where})")
            continue
        r = ratio(tokens[fg], tokens[bg])
        if r < minimum:
            problems.append(f"--{fg} on --{bg}: {r:.2f}:1, needs {minimum}:1 ({where})")
    return problems


def main(argv):
    path = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / "styles.css"
    problems = check(read_tokens(path.read_text(encoding="utf-8")))
    for p in problems:
        print(p)
    if not problems:
        print(f"contrast: all {len(PAIRS)} pairs pass")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
