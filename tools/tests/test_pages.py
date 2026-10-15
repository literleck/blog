"""The launch pages, header and footer (design spec §4, §5). In-browser tests need Google Chrome."""
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tools import probe

REPO = Path(__file__).resolve().parents[2]
PAGES = ["index.html", "games.html", "about.html", "404.html"]
PLACEHOLDERS = {"{{nnn}}", "{{slug}}", "{{title}}", "{{summary}}", "{{date_iso}}", "{{date_display}}",
                "{{og_image}}", "{{body}}", "{{prev}}", "{{next}}"}


class Static(unittest.TestCase):
    def test_every_page_has_the_basics(self):
        for page in PAGES + ["posts/_template.html"]:
            text = (REPO / page).read_text(encoding="utf-8")
            for needle in ('<html lang="en">', '<meta name="viewport"', 'class="skip" href="#content"', '<main id="content"',
                           '<header id="site" class="site"><noscript>', '<footer id="foot" class="foot"></footer>'):
                self.assertIn(needle, text, f"{page}: {needle}")

    def test_template_has_exactly_the_placeholders(self):
        text = (REPO / "posts" / "_template.html").read_text(encoding="utf-8")
        self.assertEqual(set(re.findall(r"\{\{\w+\}\}", text)), PLACEHOLDERS)

    def test_404_uses_absolute_paths(self):
        text = (REPO / "404.html").read_text(encoding="utf-8")
        self.assertIn('data-root="/blog/"', text)
        self.assertNotRegex(text, r'(href|src)="(?!/blog/|#)')

    def test_markers_appear_once_and_the_empty_feed_parses(self):  # Review Focus 1
        self.assertEqual((REPO / "index.html").read_text(encoding="utf-8").count("<!-- devlog:new -->"), 1)
        feed = (REPO / "feed.xml").read_text(encoding="utf-8")
        self.assertEqual(feed.count("<!-- feed:new -->"), 1)
        channel = ET.fromstring(feed.encode("utf-8")).find("channel")
        self.assertEqual(channel.findtext("title"), "Lord Literleck")
        self.assertEqual(channel.findall("item"), [])


@unittest.skipUnless(probe.available(), "Chrome not found")
@unittest.skipUnless(REPO.name == "blog", "the repo folder must be named blog (404.html uses /blog/ paths)")
class InBrowser(unittest.TestCase):
    def m(self, page, width, expr, js=True):
        return probe.measure(REPO, page, width, expr, js)

    def test_empty_devlog_shows_the_empty_line(self):  # Review Focus 1
        expr = 'getComputedStyle(document.querySelector(".empty")).display+"|"+getComputedStyle(document.querySelector(".entries")).display'
        self.assertEqual(self.m("index.html", 1200, expr), "block|none")

    def test_menu_marks_the_current_page(self):
        for page, current in (("index.html", "Devlog"), ("games.html", "Games"), ("about.html", "About")):
            self.assertEqual(self.m(page, 1200, 'document.querySelector("#site .menu a[aria-current=page]").textContent'), current)
        self.assertEqual(self.m("404.html", 1200, 'document.querySelectorAll("#site .menu a[aria-current]").length'), "0")

    def test_404_header_links_are_absolute(self):
        self.assertEqual(self.m("404.html", 1200, 'document.querySelector("#site .name").getAttribute("href")'), "/blog/index.html")

    def test_links_in_the_bar_on_desktop_and_in_the_footer_on_phones(self):
        expr = 'getComputedStyle(document.querySelector(".bar .links")).display+"|"+getComputedStyle(document.querySelector("#foot")).display'
        self.assertEqual(self.m("index.html", 1200, expr), "flex|none")
        self.assertEqual(self.m("index.html", 375, expr), "none|block")

    def test_external_links_carry_rel_me(self):
        self.assertEqual(self.m("index.html", 1200, 'document.querySelector("#site .links a[href^=http]").rel'), "me")

    def test_sigil_slot_is_hidden(self):
        got = self.m("index.html", 1200, 'document.querySelectorAll("#site .name").length+"|"+document.querySelectorAll("#site .sigil").length')
        self.assertEqual(got, "1|0")

    def test_no_sideways_scroll_on_a_phone(self):  # Review Focus 2
        for page in PAGES:
            got = self.m(page, 375, 'document.querySelector("main#content") ? document.documentElement.scrollWidth : "no page"')
            self.assertEqual(got, "375", page)

    def test_without_javascript_a_plain_home_link_remains(self):  # Review Focus 5
        got = self.m("index.html", 1200, 'document.querySelector("#site .name").textContent+"|"+document.querySelectorAll("#site .menu a").length', js=False)
        self.assertEqual(got, "Lord Literleck|0")


if __name__ == "__main__":
    unittest.main()
