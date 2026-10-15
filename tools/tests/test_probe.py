import tempfile
import unittest
import urllib.request
from pathlib import Path

from tools import probe

PAGE = ('<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        '<body><script>document.body.dataset.js = "on";</script></body></html>')


class Serve(unittest.TestCase):
    def test_site_appears_under_its_folder_name(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "blog"
            root.mkdir()
            (root / "p.html").write_text(PAGE, encoding="utf-8")
            with probe.serve(root) as base:
                self.assertTrue(base.endswith("/blog/"))
                with urllib.request.urlopen(base + "p.html") as r:
                    self.assertEqual(r.status, 200)


@unittest.skipUnless(probe.available(), "Chrome not found")
class Measure(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "blog"
        self.root.mkdir()
        (self.root / "p.html").write_text(PAGE, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_phone_width_below_chromes_500_px_minimum(self):
        self.assertEqual(probe.measure(self.root, "p.html", 375, "document.documentElement.clientWidth"), "375")

    def test_scripts_on_and_off(self):
        expr = "document.body.dataset.js || 'off'"
        self.assertEqual(probe.measure(self.root, "p.html", 1200, expr), "on")
        self.assertEqual(probe.measure(self.root, "p.html", 1200, expr, js=False), "off")

    def test_leaves_no_probe_files_behind(self):
        probe.measure(self.root, "p.html", 1200, "1")
        self.assertEqual(list(self.root.glob("_probe_*")), [])

    def test_screenshot_writes_a_png(self):
        out = self.root / "shot.png"
        probe.screenshot(self.root, "p.html", 375, 600, out)
        self.assertEqual(out.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
