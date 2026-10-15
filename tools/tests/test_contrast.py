import unittest

from tools import contrast
from tools.tests.token_values import TOKENS


class Ratio(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(contrast.ratio("#000000", "#ffffff"), 21.0, places=2)

    def test_same_colour_is_1(self):
        self.assertAlmostEqual(contrast.ratio("#3f5250", "#3f5250"), 1.0)

    def test_order_does_not_matter(self):
        self.assertAlmostEqual(contrast.ratio("#a0522d", "#f5f3ee"), contrast.ratio("#f5f3ee", "#a0522d"))

    def test_body_text_contrast(self):
        self.assertAlmostEqual(contrast.ratio("#464645", "#f5f3ee"), 8.52, places=2)


class Tokens(unittest.TestCase):
    def test_reads_opaque_tokens_from_root_only(self):
        css = ":root {\n  --bg: #3F5250;\n  --head-rule: #ffffff45;\n}\n.x { --title: #000000; }"
        self.assertEqual(contrast.read_tokens(css), {"bg": "#3f5250"})

    def test_no_root_block(self):
        self.assertEqual(contrast.read_tokens("body { color: red; }"), {})


class Check(unittest.TestCase):
    def test_token_values_pass(self):
        self.assertEqual(contrast.check(dict(TOKENS)), [])

    def test_reports_a_failing_pair(self):
        tokens = dict(TOKENS, muted="#9a9995")
        self.assertTrue(any(p.startswith("--muted on --paper") for p in contrast.check(tokens)))

    def test_old_comment_colour_fails(self):
        tokens = dict(TOKENS, **{"hl-comment": "#8d929b"})
        self.assertTrue(any(p.startswith("--hl-comment on --code-bg") for p in contrast.check(tokens)))

    def test_reports_a_missing_token(self):
        tokens = dict(TOKENS)
        del tokens["rust"]
        self.assertTrue(any("missing token --rust" in p for p in contrast.check(tokens)))


if __name__ == "__main__":
    unittest.main()
