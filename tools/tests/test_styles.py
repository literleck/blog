import re
import unittest
from pathlib import Path

from tools import contrast
from tools.tests.spec_values import TOKENS

CSS = (Path(__file__).resolve().parents[2] / "styles.css").read_text(encoding="utf-8")


class Tokens(unittest.TestCase):
    def test_tokens_are_the_spec_values(self):
        tokens = contrast.read_tokens(CSS)
        for name, value in TOKENS.items():
            self.assertEqual(tokens.get(name), value, f"--{name}")

    def test_contrast_passes(self):
        self.assertEqual(contrast.check(contrast.read_tokens(CSS)), [])

    def test_translucent_tokens(self):
        for decl in ("--head-rule: #ffffff45;", "--rust-line: #a0522d66;", "--shadow: drop-shadow(5px 5px 0 #0000004d);"):
            self.assertIn(decl, CSS)


class Rules(unittest.TestCase):
    def test_no_web_fonts_and_no_motion(self):
        for banned in ("@font-face", "@import", "fonts.googleapis", "animation", "transition"):
            self.assertNotIn(banned, CSS)

    def test_reading_type(self):
        self.assertRegex(CSS, r"article p, article li \{ font: 17px/1\.7 var\(--serif\); color: var\(--text\); text-align: justify; hyphens: auto;")

    def test_long_words_wrap_instead_of_widening_the_page(self):  # Review Focus 2
        for selector in ("article p, article li", "article h1", ".entry h2", ".site .name", ".prevnext a"):
            block = re.search(re.escape(selector) + r" \{([^}]*)\}", CSS)
            self.assertIsNotNone(block, selector)
            self.assertIn("overflow-wrap: anywhere", block.group(1), selector)

    def test_phone_rules(self):
        phone = CSS[CSS.index("@media (max-width: 640px)"):]
        self.assertIn(".bar .links { display: none; }", phone)
        self.assertIn(".foot { display: block;", phone)
        self.assertIn(".site .name { font-size: 28px; }", phone)

    def test_desktop_links_wrap_on_the_right(self):
        self.assertRegex(CSS, r"\.links \{ flex: 1 1 auto; display: flex; flex-wrap: wrap; justify-content: flex-end;")


if __name__ == "__main__":
    unittest.main()
