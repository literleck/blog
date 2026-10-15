import tempfile
import unittest
from pathlib import Path

from tools import check_site
from tools.tests.sitefixture import make_site, name, post


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def errors(self, root):
        return check_site.check(root)[0]

    def edit(self, path, old, new):
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")


class Dates(unittest.TestCase):
    def test_display_date(self):
        self.assertEqual(check_site.display_date("2027-02-14"), "2027 Feb 14")
        self.assertEqual(check_site.display_date("2026-11-02"), "2026 Nov 2")

    def test_rfc822_is_noon_gmt(self):
        self.assertEqual(check_site.rfc822("2027-02-14"), "Sun, 14 Feb 2027 12:00:00 GMT")


class GoodSites(Base):
    def test_empty_blog_passes(self):
        self.assertEqual(self.errors(make_site(self.tmp)), [])

    def test_three_posts_pass(self):
        root = make_site(self.tmp, [post(1), post(2, thumb=True), post(3)])
        self.assertEqual(self.errors(root), [])

    def test_special_characters_pass_and_feed_parses(self):
        p = post(1, title='Tom & Jerry: <pointers> "explained"', summary="Why a < b & c > d isn't scary.")
        self.assertEqual(self.errors(make_site(self.tmp, [p])), [])

    def test_gap_in_numbers_links_across_it(self):
        self.assertEqual(self.errors(make_site(self.tmp, [post(1), post(3)])), [])


class BrokenSites(Base):
    def test_missing_required_file(self):
        root = make_site(self.tmp)
        (root / "feed.xml").unlink()
        self.assertIn("missing required file feed.xml", self.errors(root))

    def test_broken_link(self):
        root = make_site(self.tmp)
        self.edit(root / "about.html", 'href="index.html">Lord', 'href="nowhere.html">Lord')
        self.assertTrue(any("broken link nowhere.html" in e for e in self.errors(root)))

    def test_duplicate_number(self):
        root = make_site(self.tmp, [post(1), post(2)])
        (root / "posts" / "002-other.html").write_text((root / "posts" / name(post(2))).read_text(encoding="utf-8"), encoding="utf-8")
        self.assertTrue(any("#002 is already used" in e for e in self.errors(root)))

    def test_first_post_with_a_previous_link(self):
        root = make_site(self.tmp, [post(1), post(2)])
        self.edit(root / "posts" / name(post(1)), '<nav class="prevnext" aria-label="More posts">',
                  '<nav class="prevnext" aria-label="More posts"><a class="prev" href="000-x.html">◂ #000 X</a>')
        self.assertTrue(any("has a previous link but there is no previous post" in e for e in self.errors(root)))

    def test_newest_post_missing_from_previous_next(self):
        root = make_site(self.tmp, [post(1), post(2)])
        self.edit(root / "posts" / name(post(1)), f'<a class="next" href="{name(post(2))}">#002 ▸</a>', "")
        self.assertTrue(any("next link missing" in e for e in self.errors(root)))

    def test_entry_missing_from_devlog(self):
        root = make_site(self.tmp, [post(1)])
        text = (root / "index.html").read_text(encoding="utf-8")
        start, end = text.index('<li class="entry'), text.index("</li>") + len("</li>")
        (root / "index.html").write_text(text[:start] + text[end:], encoding="utf-8")
        self.assertTrue(any("index.html: entries are []" in e for e in self.errors(root)))

    def test_unescaped_ampersand_in_feed(self):
        root = make_site(self.tmp, [post(1, title="Tom and Jerry")])
        self.edit(root / "feed.xml", "<title>Tom and Jerry</title>", "<title>Tom & Jerry</title>")
        self.assertTrue(any("not well-formed XML" in e for e in self.errors(root)))

    def test_wrong_date_tab(self):
        root = make_site(self.tmp, [post(1)])
        self.edit(root / "posts" / name(post(1)), ">2027 Feb 14</time>", ">2027 Feb 15</time>")
        self.assertTrue(any("date tab reads" in e for e in self.errors(root)))

    def test_image_without_alt_text(self):
        root = make_site(self.tmp, [post(1, body='<figure><img src="../assets/favicon.svg" alt=""></figure>')])
        self.assertTrue(any("image ../assets/favicon.svg has no alt text" in e for e in self.errors(root)))

    def test_markdown_source_must_match(self):
        root = make_site(self.tmp, [post(1)])
        (root / "posts" / "001-post-1.md").write_text('---\nnumber: 1\ntitle: "Another title"\ndate: 2027-02-14\nslug: post-1\n'
                                                      'summary: "Summary of post 1."\n---\nBody text.\n', encoding="utf-8")
        self.assertTrue(any("001-post-1.md: title is 'Another title'" in e for e in self.errors(root)))


class Media(Base):
    def test_wide_image_is_a_warning_not_an_error(self):
        root = make_site(self.tmp, [post(1)])
        (root / "media" / "001-post-1").mkdir(parents=True)
        (root / "media" / "001-post-1" / "wide.png").write_bytes(b"\x89PNG\r\n\x1a\n\0\0\0\rIHDR" + (2400).to_bytes(4, "big") + (100).to_bytes(4, "big"))
        errors, warnings = check_site.check(root)
        self.assertEqual(errors, [])
        self.assertTrue(any("2400 px wide" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
