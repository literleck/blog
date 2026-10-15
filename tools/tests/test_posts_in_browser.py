"""Published posts in a throwaway copy of the site, in headless Chrome."""
import tempfile
import unittest
from pathlib import Path

from tools import probe
from tools.tests.sitefixture import make_site, post

LONG_BODY = ("<p>See https://example.com/" + "a" * 120 + " and <code>" + "an_extremely_long_identifier_" * 3 + "</code>.</p>"
             '<pre><code class="language-c">int x = 1; // ' + "x" * 200 + "</code></pre>")


@unittest.skipUnless(probe.available(), "Chrome not found")
class Posts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = make_site(cls._tmp.name, [post(1, title="A" * 90, body=LONG_BODY), post(2, thumb=True)])

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def m(self, page, width, expr, js=True):
        return probe.measure(self.root, page, width, expr, js)

    def test_devlog_with_posts_hides_the_empty_line(self):
        self.assertEqual(self.m("index.html", 1200, 'getComputedStyle(document.querySelector(".empty")).display'), "none")

    def test_post_header_links_go_up_one_level(self):
        self.assertEqual(self.m("posts/001-post-1.html", 1200, 'document.querySelector("#site .name").getAttribute("href")'), "../index.html")
        self.assertEqual(self.m("posts/001-post-1.html", 1200, 'document.querySelector("#site .menu a[aria-current=page]").textContent'), "Devlog")

    def test_long_words_and_code_never_widen_the_page(self):
        for page in ("index.html", "posts/001-post-1.html", "posts/002-post-2.html"):
            got = self.m(page, 375, 'document.querySelector("main#content") ? document.documentElement.scrollWidth : "no page"')
            self.assertEqual(got, "375", page)

    def test_code_is_highlighted(self):
        self.assertEqual(self.m("posts/001-post-1.html", 1200, 'document.querySelectorAll("pre .hljs-comment").length'), "1")

    def test_post_reads_without_javascript(self):
        got = self.m("posts/001-post-1.html", 375, 'document.querySelector("article h1").textContent.length+"|"+document.documentElement.scrollWidth', js=False)
        self.assertEqual(got, "90|375")


if __name__ == "__main__":
    unittest.main()
