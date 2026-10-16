"""Check the blog for broken links and for the post format (design spec §6 and §10).

Usage: python3 tools/check_site.py [site root]
Prints every problem; exit status 1 if there are errors. Media-limit findings are warnings only.
       python3 tools/check_site.py --next [site root]
Prints the next post's number (one more than the highest ever published, retired numbers included).
"""
import datetime
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE_URL = "https://literleck.github.io/blog/"
NAME = "Lord Literleck"
REQUIRED = ["index.html", "games.html", "about.html", "404.html", "feed.xml", "styles.css", "header.js", ".nojekyll",
            "posts/_template.html", "assets/overworld.svg", "assets/favicon.svg", "assets/social.png",
            "assets/hl/init.js", "assets/hl/core.min.js", "assets/hl/languages/c.min.js", "assets/hl/languages/bash.min.js"]
POST_NAME = re.compile(r"^(\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)\.html$")
MAX_WIDTH, MAX_GIF = 1600, 8 * 1024 * 1024
# Spec §6.3: the only elements a post body may contain.
BODY_TAGS = {"p", "h2", "h3", "em", "strong", "a", "ul", "ol", "li", "blockquote", "code", "pre", "figure", "img", "video", "figcaption"}


def display_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.year} {d.strftime('%b')} {d.day}"


def rfc822(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.strftime('%a')}, {d.day:02d} {d.strftime('%b')} {d.year} 12:00:00 GMT"


class Page(HTMLParser):
    """Collects what the checks need from one HTML page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.meta, self.title, self.h1, self.imgs = [], {}, "", "", []
        self.tabs, self.entries, self.prev, self.next = [], [], None, None
        self._stack, self._in, self._entry, self._link = [], None, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("href", "src"):
            if a.get(key) and tag in ("a", "link", "script", "img", "video", "source"):
                self.refs.append(a[key])
        if tag == "meta" and (a.get("property") or a.get("name")):
            self.meta[a.get("property") or a.get("name")] = a.get("content", "")
        cls = a.get("class", "")
        if tag == "img":
            self.imgs.append({"src": a.get("src", ""), "alt": a.get("alt", ""), "class": cls})
        if tag == "li" and "entry" in cls.split():
            self._entry = {"tab": "", "datetime": "", "href": "", "title": "", "summary": "", "thumb": None, "card": ""}
            self.entries.append(self._entry)
        if tag == "span" and "tab" in cls.split():
            self._in = "tab"
            self.tabs.append({"text": "", "datetime": ""})
        if tag == "time" and self._in == "tab":
            self.tabs[-1]["datetime"] = a.get("datetime", "")
            if self._entry is not None:
                self._entry["datetime"] = a.get("datetime", "")
        if tag == "div" and self._entry is not None and "card" in cls.split():
            self._entry["card"] = cls
        if tag in ("title", "h1"):
            self._in = tag
        if tag == "a" and self._entry is not None and self._in == "h2":
            self._entry["href"] = a.get("href", "")
        if tag == "h2" and self._entry is not None:
            self._in = "h2"
        if tag == "p" and self._entry is not None:
            self._in = "summary"
        if tag == "img" and self._entry is not None and "thumb" in cls.split():
            self._entry["thumb"] = a.get("src")
        if tag == "a" and "prev" in cls.split():
            self.prev = {"href": a.get("href", ""), "text": ""}
            self._link = self.prev
        if tag == "a" and "next" in cls.split():
            self.next = {"href": a.get("href", ""), "text": ""}
            self._link = self.next

    def handle_endtag(self, tag):
        if {"title": "title", "h1": "h1", "h2": "h2", "p": "summary", "span": "tab"}.get(tag) == self._in:
            self._in = None
        if tag == "li":
            self._entry = None
        if tag == "a":
            self._link = None

    def handle_data(self, data):
        if self._link is not None:
            self._link["text"] += data
        if self._in == "title":
            self.title += data
        elif self._in == "h1":
            self.h1 += data
        elif self._in == "tab":
            self.tabs[-1]["text"] += data
            if self._entry is not None:
                self._entry["tab"] += data
        elif self._in == "h2" and self._entry is not None:
            self._entry["title"] += data
        elif self._in == "summary" and self._entry is not None:
            self._entry["summary"] += data


def parse(path):
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    for e in p.entries:
        e["tab"] = " ".join(e["tab"].split())
    for t in p.tabs:
        t["text"] = " ".join(t["text"].split())
    p.title, p.h1 = " ".join(p.title.split()), " ".join(p.h1.split())
    return p


def exists_exact(root, target):
    """True if target exists with exactly this letter case (the Mac ignores case; GitHub Pages does not)."""
    target = Path(os.path.normpath(target))
    if not target.exists():
        return False
    try:
        parts = target.relative_to(root).parts
    except ValueError:
        return True
    here = root
    for part in parts:
        if part not in os.listdir(here):
            return False
        here = here / part
    return True


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.videos = [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "video":
            self.videos.append(dict(attrs))


def read_retired(root):
    """Numbers of deleted posts, from posts/retired.txt (one three-digit number per line). Returns (numbers, errors)."""
    path = root / "posts" / "retired.txt"
    numbers, errors = set(), []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines() if path.exists() else [], 1):
        if not line.strip():
            continue
        if re.fullmatch(r"\d{3}", line.strip()):
            numbers.add(int(line))
        else:
            errors.append(f"posts/retired.txt line {i}: '{line}' is not a three-digit number")
    return numbers, errors


def next_number(root):
    """Spec §6.2: one more than the highest number ever published, retired numbers included."""
    root = Path(root)
    used = {int(m.group(1)) for f in (root / "posts").glob("*.html") if (m := POST_NAME.match(f.name))}
    return max(used | read_retired(root)[0], default=0) + 1


def template_pattern(template):
    """A regex for a post built from the template: placeholders become groups, everything else must match exactly."""
    out, seen = [], set()
    for piece in re.split(r"(\{\{\w+\}\})", template):
        m = re.fullmatch(r"\{\{(\w+)\}\}", piece)
        if m:
            out.append(f"(?P={m.group(1)})" if m.group(1) in seen else f"(?P<{m.group(1)}>.*?)")
            seen.add(m.group(1))
        else:
            out.append(re.escape(piece))
    return re.compile("".join(out) + r"\Z", re.S)


def check_links(root, html_files):
    errors = []
    for f in html_files:
        for ref in parse(f).refs:
            parts = urlsplit(ref)
            if parts.scheme or ref.startswith(("#", "mailto:")) or not parts.path:
                continue
            path = unquote(parts.path)
            target = root / path[len("/blog/"):] if path.startswith("/blog/") else (f.parent / path)
            if path.startswith("/") and not path.startswith("/blog/"):
                errors.append(f"{f.relative_to(root)}: absolute link outside /blog/: {ref}")
            elif not exists_exact(root, target):
                errors.append(f"{f.relative_to(root)}: broken link {ref} (missing, or the letter case differs)")
    return errors


def image_width(path):
    data = path.read_bytes()[:64 * 1024]
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">I", data[16:20])[0]
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<H", data[6:8])[0]
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                return struct.unpack(">H", data[i + 7:i + 9])[0]
            i += 2 + length
    return None


def check_media(root):
    warnings = []
    media = root / "media"
    for f in sorted(media.rglob("*")) if media.exists() else []:
        if not f.is_file():
            continue
        rel = f.relative_to(root)
        if f.suffix.lower() == ".gif" and f.stat().st_size > MAX_GIF:
            warnings.append(f"{rel}: GIF over 8 MB; publish it as MP4 or WebM")
        if f.suffix.lower() in (".png", ".gif", ".jpg", ".jpeg"):
            w = image_width(f)
            if w and w > MAX_WIDTH:
                warnings.append(f"{rel}: {w} px wide, over {MAX_WIDTH} px")
    return warnings


def _scalar(raw):
    """A header-block value: "double-quoted" (backslash escapes), 'single-quoted' ('' is a quote) or bare; # starts a comment outside quotes."""
    raw = raw.strip()
    if raw.startswith('"'):
        m = re.match(r'"((?:[^"\\]|\\.)*)"\s*(#.*)?$', raw)
        return re.sub(r"\\(.)", r"\1", m.group(1)) if m else raw
    if raw.startswith("'"):
        m = re.match(r"'((?:[^']|'')*)'\s*(#.*)?$", raw)
        return m.group(1).replace("''", "'") if m else raw
    return re.split(r"\s+#", raw, maxsplit=1)[0].strip()


def read_front_matter(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return None
    out = {}
    for line in lines[1:]:
        if line == "---":
            return out
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = _scalar(m.group(2))
    return None


def check_posts(root):
    retired, errors = read_retired(root)
    posts = {}
    pattern = template_pattern((root / "posts" / "_template.html").read_text(encoding="utf-8"))
    for f in sorted((root / "posts").glob("*.html")):
        if f.name == "_template.html":
            continue
        m = POST_NAME.match(f.name)
        if not m:
            errors.append(f"posts/{f.name}: name is not NNN-slug.html")
            continue
        n = int(m.group(1))
        if n in retired:
            errors.append(f"posts/{f.name}: number #{m.group(1)} is retired (posts/retired.txt); numbers are never reused")
        if n in posts:
            errors.append(f"posts/{f.name}: number #{m.group(1)} is already used by posts/{posts[n]['file'].name}")
            continue
        text = f.read_text(encoding="utf-8")
        fit = pattern.match(text)
        if not fit:
            errors.append(f"posts/{f.name}: does not follow posts/_template.html (only the placeholders may differ)")
        else:
            tags = Tags()
            tags.feed(fit.group("body"))
            for tag in sorted(set(tags.tags) - BODY_TAGS):
                errors.append(f"posts/{f.name}: <{tag}> is not in the allowed set of body elements (spec §6.3)")
            for v in tags.videos:
                if "autoplay" in v:
                    errors.append(f"posts/{f.name}: video {v.get('src')} has autoplay; videos wait for a click (spec §6.3)")
                for attr in ("controls", "muted"):
                    if attr not in v:
                        errors.append(f"posts/{f.name}: video {v.get('src')} needs the {attr} attribute (spec §6.3)")
        p = parse(f)
        tab = p.tabs[0] if p.tabs else {"text": "", "datetime": ""}
        posts[n] = {"file": f, "nnn": m.group(1), "slug": m.group(2), "page": p, "date": tab["datetime"], "title": p.h1,
                    "summary": p.meta.get("description", "")}
    numbers = sorted(posts)
    for i, n in enumerate(numbers):
        post, p, where = posts[n], posts[n]["page"], f"posts/{posts[n]['file'].name}"
        try:
            shown = display_date(post["date"])
        except ValueError:
            errors.append(f"{where}: date tab has no valid <time datetime=YYYY-MM-DD>")
            continue
        if p.tabs[0]["text"] != f"#{post['nnn']} · {shown}":
            errors.append(f"{where}: date tab reads '{p.tabs[0]['text']}', expected '#{post['nnn']} · {shown}'")
        if not post["title"]:
            errors.append(f"{where}: no <h1> title")
        if p.title != f"{post['title']} · {NAME}":
            errors.append(f"{where}: <title> is '{p.title}', expected '{post['title']} · {NAME}'")
        if not post["summary"] or p.meta.get("og:description") != post["summary"]:
            errors.append(f"{where}: description and og:description must be the same, non-empty summary")
        if p.meta.get("og:title") != post["title"]:
            errors.append(f"{where}: og:title does not match the <h1>")
        url = f"{SITE_URL}posts/{post['file'].name}"
        if p.meta.get("og:url") != url:
            errors.append(f"{where}: og:url should be {url}")
        og = p.meta.get("og:image", "")
        if not og.startswith(SITE_URL):
            errors.append(f"{where}: og:image must be an absolute URL under {SITE_URL}")
        elif not exists_exact(root, root / og[len(SITE_URL):]):
            errors.append(f"{where}: og:image {og} points to a file that does not exist")
        for img in p.imgs:
            if "thumb" not in img["class"].split() and not img["alt"].strip():
                errors.append(f"{where}: image {img['src']} has no alt text")
        prev = posts[numbers[i - 1]] if i > 0 else None
        nxt = posts[numbers[i + 1]] if i + 1 < len(numbers) else None
        for label, link, want, text in (("previous", p.prev, prev, lambda q: f"◂ #{q['nnn']} {q['title']}"),
                                        ("next", p.next, nxt, lambda q: f"#{q['nnn']} ▸")):
            if want is None and link is not None:
                errors.append(f"{where}: has a {label} link but there is no {label} post")
            elif want is not None and link is None:
                errors.append(f"{where}: {label} link missing (should point to {want['file'].name})")
            elif want is not None:
                if link["href"] != want["file"].name:
                    errors.append(f"{where}: {label} link points to {link['href']}, expected {want['file'].name}")
                if " ".join(link["text"].split()) != text(want):
                    errors.append(f"{where}: {label} link reads '{' '.join(link['text'].split())}', expected '{text(want)}'")
        md = post["file"].with_suffix(".md")
        if md.exists():
            fm = read_front_matter(md)
            if fm is None:
                errors.append(f"posts/{md.name}: no header block between --- lines")
            else:
                for key, have in (("number", str(n)), ("slug", post["slug"]), ("title", post["title"]),
                                  ("date", post["date"]), ("summary", post["summary"])):
                    if fm.get(key) != have:
                        errors.append(f"posts/{md.name}: {key} is '{fm.get(key)}', the page has '{have}'")
    return posts, errors


def check_devlog(root, posts):
    errors = []
    text = (root / "index.html").read_text(encoding="utf-8")
    if text.count("<!-- devlog:new -->") != 1:
        return ["index.html: the marker <!-- devlog:new --> must appear exactly once"]
    before, after = text.split("<!-- devlog:new -->")
    if 'class="entry' in before:
        errors.append("index.html: a Devlog entry sits above the <!-- devlog:new --> marker")
    entries = parse(root / "index.html").entries
    want = sorted(posts, reverse=True)
    got = []
    for e in entries:
        m = re.match(r"^posts/(\d{3})-", e["href"])
        if not m:
            errors.append(f"index.html: entry links to '{e['href']}', not a post")
            continue
        got.append(int(m.group(1)))
        post = posts.get(int(m.group(1)))
        if post is None:
            errors.append(f"index.html: entry links to {e['href']}, which does not exist")
            continue
        if e["href"] != f"posts/{post['file'].name}":
            errors.append(f"index.html: entry #{post['nnn']} links to {e['href']}, expected posts/{post['file'].name}")
        if e["tab"] != f"#{post['nnn']} · {display_date(post['date'])}":
            errors.append(f"index.html: entry #{post['nnn']} tab reads '{e['tab']}'")
        if e["datetime"] != post["date"]:
            errors.append(f"index.html: entry #{post['nnn']} <time datetime> is '{e['datetime']}', expected '{post['date']}'")
        if bool(e["thumb"]) == ("text-only" in e["card"].split()):
            errors.append(f"index.html: entry #{post['nnn']} has a thumbnail but the class text-only, or neither" if e["thumb"]
                          else f"index.html: entry #{post['nnn']} has no thumbnail, so its card needs the class text-only")
        if " ".join(e["title"].split()) != post["title"]:
            errors.append(f"index.html: entry #{post['nnn']} title differs from the post's <h1>")
        if " ".join(e["summary"].split()) != post["summary"]:
            errors.append(f"index.html: entry #{post['nnn']} summary differs from the post's description")
    if got != want:
        errors.append(f"index.html: entries are {['#%03d' % n for n in got]}, expected {['#%03d' % n for n in want]} (newest first, one each)")
    return errors


def check_feed(root, posts):
    text = (root / "feed.xml").read_text(encoding="utf-8")
    if text.count("<!-- feed:new -->") != 1:
        return ["feed.xml: the marker <!-- feed:new --> must appear exactly once"]
    if "<item>" in text.split("<!-- feed:new -->")[0]:
        return ["feed.xml: an item sits above the <!-- feed:new --> marker"]
    try:
        channel = ET.fromstring(text.encode("utf-8")).find("channel")
    except ET.ParseError as exc:
        return [f"feed.xml: not well-formed XML ({exc}); check & < > in titles and summaries"]
    errors, got = [], []
    for item in channel.findall("item"):
        link = item.findtext("link", "")
        m = re.match(re.escape(SITE_URL) + r"posts/(\d{3})-[a-z0-9-]+\.html$", link)
        if not m or int(m.group(1)) not in posts:
            errors.append(f"feed.xml: item links to '{link}', not an existing post")
            continue
        n = int(m.group(1))
        got.append(n)
        post = posts[n]
        checks = (("title", post["title"]), ("guid", link), ("description", post["summary"]), ("pubDate", rfc822(post["date"])))
        if item.find("guid") is None or item.find("guid").get("isPermaLink") != "true":
            errors.append(f"feed.xml: item #{post['nnn']} guid needs isPermaLink=\"true\"")
        for tag, want in checks:
            if item.findtext(tag, "").strip() != want:
                errors.append(f"feed.xml: item #{post['nnn']} {tag} is '{item.findtext(tag, '').strip()}', expected '{want}'")
    want = sorted(posts, reverse=True)
    if got != want:
        errors.append(f"feed.xml: items are {['#%03d' % n for n in got]}, expected {['#%03d' % n for n in want]} (newest first, one each)")
    return errors


def check(root):
    root = Path(root).resolve()
    errors = [f"missing required file {r}" for r in REQUIRED if not (root / r).exists()]
    if errors:
        return errors, []
    html_files = sorted(f for f in root.rglob("*.html") if f.name != "_template.html" and not f.name.startswith("_probe_"))
    errors += check_links(root, html_files)
    posts, post_errors = check_posts(root)
    errors += post_errors
    errors += check_devlog(root, posts)
    errors += check_feed(root, posts)
    return errors, check_media(root)


def main(argv):
    args = argv[1:]
    want_next = "--next" in args
    args = [a for a in args if a != "--next"]
    root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    if want_next:
        print(f"{next_number(root):03d}")
        return 0
    errors, warnings = check(root)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("error:", e)
    if not errors:
        print("check_site: no errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
