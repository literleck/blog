"""Published posts in a throwaway copy of the site, in headless Chrome."""
import tempfile
import unittest
from pathlib import Path

from tools import probe
from tools.tests.sitefixture import make_site, post

HEADING_BODY = ("<h2>handle_paddle_collision_response_" + "x" * 20 + "</h2>"
                "<h3>https://example.com/" + "b" * 80 + "</h3><p>Short.</p>")
LONG_BODY = ("<p>See https://example.com/" + "a" * 120 + " and <code>" + "an_extremely_long_identifier_" * 3 + "</code>.</p>"
             '<pre><code class="language-c">int x = 1; // ' + "x" * 200 + "</code></pre>")


@unittest.skipUnless(probe.available(), "Chrome not found")
class Posts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = make_site(cls._tmp.name, [post(1, title="A" * 90, body=LONG_BODY), post(2, thumb=True), post(3, body=HEADING_BODY)])
        about = cls.root / "about.html"
        about.write_text(about.read_text(encoding="utf-8").replace(
            "This page is waiting for its author.", "My links: https://example.com/" + "c" * 90), encoding="utf-8")
        index = cls.root / "index.html"
        index.write_text(index.read_text(encoding="utf-8").replace(
            "<span>Orientation</span>", "<span>Pong · " + "the_longest_quest_name_" * 3 + "</span>"), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def m(self, page, width, expr, js=True):
        return probe.measure(self.root, page, width, expr, js)

    def test_devlog_with_posts_hides_the_empty_line(self):
        self.assertEqual(self.m("index.html", 1200, 'getComputedStyle(document.querySelector(".empty")).display'), "none")

    def test_post_header_links_go_up_one_level(self):
        self.assertEqual(self.m("posts/001-post-1.html", 1200, 'document.querySelector("#site .name").getAttribute("href")'), "../index.html")

    def test_post_marks_devlog_as_its_section_not_its_page(self):
        expr = ('document.querySelectorAll("#site .menu a[aria-current=page]").length+"|"'
                '+document.querySelector("#site .menu a[aria-current=true]").textContent+"|"'
                '+getComputedStyle(document.querySelector("#site .menu a[aria-current]"), "::before").content')
        self.assertEqual(self.m("posts/001-post-1.html", 1200, expr), '0|Devlog|"▸"')

    def test_prev_next_nav_shows_only_when_it_has_links(self):
        self.assertEqual(self.m("posts/002-post-2.html", 1200, 'getComputedStyle(document.querySelector(".prevnext")).display'), "flex")
        with tempfile.TemporaryDirectory() as tmp:
            lone = make_site(tmp, [post(1)])
            self.assertEqual(probe.measure(lone, "posts/001-post-1.html", 1200, 'getComputedStyle(document.querySelector(".prevnext")).display'), "none")

    def test_long_words_and_code_never_widen_the_page(self):
        for page in ("index.html", "posts/001-post-1.html", "posts/002-post-2.html"):
            got = self.m(page, 375, 'document.querySelector("main#content") ? document.documentElement.scrollWidth : "no page"')
            self.assertEqual(got, "375", page)

    def test_long_headings_never_widen_the_page(self):
        got = self.m("posts/003-post-3.html", 375, 'document.querySelector("main#content") ? document.documentElement.scrollWidth : "no page"')
        self.assertEqual(got, "375")

    def test_long_about_text_and_quest_never_widen_the_page(self):
        for page in ("about.html", "index.html"):
            got = self.m(page, 375, 'document.querySelector("main#content") ? document.documentElement.scrollWidth : "no page"')
            self.assertEqual(got, "375", page)

    def test_code_block_scrolls_inside_itself(self):
        got = self.m("posts/001-post-1.html", 375, '(function(p){return p.scrollWidth > p.clientWidth})(document.querySelector("pre"))')
        self.assertEqual(got, "true")

    def test_code_is_highlighted(self):
        self.assertEqual(self.m("posts/001-post-1.html", 1200, 'document.querySelectorAll("pre .hljs-comment").length'), "1")

    def test_post_reads_without_javascript(self):
        got = self.m("posts/001-post-1.html", 375, 'document.querySelector("article h1").textContent.length+"|"+document.documentElement.scrollWidth', js=False)
        self.assertEqual(got, "90|375")


if __name__ == "__main__":
    unittest.main()
