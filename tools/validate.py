"""Validate every page with the W3C Nu HTML checker and the feed with the W3C feed validator (design spec §10, checks 1 and 4).

Sends the files to validator.w3.org, so it needs the network. The content is public anyway.
Usage: python3 tools/validate.py [site root]
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "literleck-blog-check/1.0"


def nu(path):
    req = urllib.request.Request("https://validator.w3.org/nu/?out=json", data=path.read_bytes(),
                                 headers={"Content-Type": "text/html; charset=utf-8", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        messages = json.load(r)["messages"]
    return [f"{m.get('lastLine', '?')}: {m['message']}" for m in messages if m.get("type") == "error"]


def feed(path):
    data = urllib.parse.urlencode({"rawdata": path.read_text(encoding="utf-8"), "output": "soap12"}).encode()
    req = urllib.request.Request("https://validator.w3.org/feed/check.cgi", data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8")
    if "<m:validity>true</m:validity>" in body:
        return []
    return re.findall(r"<text>(.*?)</text>", body) or ["feed validator: not valid"]


def main(argv):
    root = Path(argv[1] if len(argv) > 1 else Path(__file__).resolve().parent.parent).resolve()
    failures = 0
    files = [root / p for p in ("index.html", "games.html", "about.html", "404.html")] + sorted((root / "posts").glob("[0-9][0-9][0-9]-*.html"))
    for f in files:
        errors = nu(f)
        print(f"{f.relative_to(root)}: {'ok' if not errors else ''}")
        for e in errors:
            print("  ", e)
        failures += bool(errors)
        time.sleep(1)
    errors = feed(root / "feed.xml")
    print(f"feed.xml: {'ok' if not errors else ''}")
    for e in errors:
        print("  ", e)
    failures += bool(errors)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
