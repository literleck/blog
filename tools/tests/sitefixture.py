"""Build throwaway copies of the blog with posts in them, rendered exactly as a published post must be.

Tests use it to exercise check_site.py against the real template and pages.
"""
import html
import re
import shutil
from pathlib import Path

from tools.check_site import SITE_URL, display_date, rfc822, updated_slot

REPO = Path(__file__).resolve().parents[2]
COPY = ["index.html", "games.html", "about.html", "404.html", "feed.xml", "styles.css", "header.js", ".nojekyll", "posts/_template.html", "assets"]


def post(number, title=None, date="2027-02-14", slug=None, summary=None, thumb=False, body="<p>Body text.</p>", updated=None):
    return {"number": number, "nnn": f"{number:03d}", "title": title or f"Post {number}", "date": date,
            "slug": slug or f"post-{number}", "summary": summary or f"Summary of post {number}.", "thumb": thumb, "body": body,
            "updated": updated}


def name(p):
    return f"{p['nnn']}-{p['slug']}.html"


def render_post(template, p, prev, nxt):
    og = f"{SITE_URL}media/{p['nnn']}-{p['slug']}/thumb.png" if p["thumb"] else f"{SITE_URL}assets/social.png"
    prev_html = f'<a class="prev" href="{name(prev)}">◂ #{prev["nnn"]} {html.escape(prev["title"])}</a>' if prev else ""
    next_html = f'<a class="next" href="{name(nxt)}">#{nxt["nnn"]} ▸</a>' if nxt else ""
    values = {"nnn": p["nnn"], "slug": p["slug"], "title": html.escape(p["title"]), "summary": html.escape(p["summary"]),
              "date_iso": p["date"], "date_display": display_date(p["date"]), "og_image": og, "body": p["body"],
              "prev": prev_html, "next": next_html, "updated": updated_slot(p["updated"])}
    out = template
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def devlog_entry(p):
    thumb = f'<img class="thumb" src="media/{p["nnn"]}-{p["slug"]}/thumb.png" alt="">' if p["thumb"] else ""
    cls = "card" if p["thumb"] else "card text-only"
    return (f'<li class="entry tabbed">\n  <span class="tab">#{p["nnn"]} · <time datetime="{p["date"]}">{display_date(p["date"])}</time></span>\n'
            f'  <div class="win"><div class="{cls}">\n    {thumb}\n'
            f'    <div><h2><a href="posts/{name(p)}">{html.escape(p["title"])}</a></h2>\n      <p>{html.escape(p["summary"])}</p></div>\n'
            f'  </div></div>\n</li>\n')


def feed_item(p):
    url = f"{SITE_URL}posts/{name(p)}"
    return (f"<item>\n  <title>{html.escape(p['title'], quote=False)}</title>\n  <link>{url}</link>\n"
            f'  <guid isPermaLink="true">{url}</guid>\n  <pubDate>{rfc822(p["date"])}</pubDate>\n'
            f"  <description>{html.escape(p['summary'], quote=False)}</description>\n</item>\n")


def make_site(tmp, posts=()):
    """Copy the real site into tmp/blog without its live posts and publish `posts` (oldest first). Returns the site root."""
    root = Path(tmp) / "blog"
    for item in COPY:
        src, dst = REPO / item, root / item
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
    for f, pattern in (("index.html", r'<li class="entry tabbed">.*?</li>\n'), ("feed.xml", r"<item>.*?</item>\n")):
        path = root / f  # start from an empty Devlog and feed: the real ones hold the live posts
        path.write_text(re.sub(pattern, "", path.read_text(encoding="utf-8"), flags=re.S), encoding="utf-8")
    (root / "assets" / "social.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 24)
    template = (root / "posts" / "_template.html").read_text(encoding="utf-8")
    ordered = sorted(posts, key=lambda q: q["number"])
    for i, p in enumerate(ordered):
        prev = ordered[i - 1] if i > 0 else None
        nxt = ordered[i + 1] if i + 1 < len(ordered) else None
        (root / "posts" / name(p)).write_text(render_post(template, p, prev, nxt), encoding="utf-8")
        if p["thumb"]:
            (root / "media" / f"{p['nnn']}-{p['slug']}").mkdir(parents=True, exist_ok=True)
            (root / "media" / f"{p['nnn']}-{p['slug']}" / "thumb.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + (640).to_bytes(4, "big") + (400).to_bytes(4, "big"))
    for p in ordered:  # newest ends up on top, as when publishing one by one
        for f, marker, block in (("index.html", "<!-- devlog:new -->", devlog_entry(p)), ("feed.xml", "<!-- feed:new -->", feed_item(p))):
            path = root / f
            path.write_text(path.read_text(encoding="utf-8").replace(marker, marker + "\n" + block, 1), encoding="utf-8")
    return root
