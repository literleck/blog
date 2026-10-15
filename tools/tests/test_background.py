import re
import unittest
from collections import Counter

from tools import make_background as mb


class Tiles(unittest.TestCase):
    def test_every_tile_is_8_by_8_with_a_palette_entry_per_character(self):
        for name, rows in mb.TILES.items():
            self.assertEqual(len(rows), 8, name)
            for row in rows:
                self.assertEqual(len(row), 8, name)
                for ch in row:
                    self.assertIn(ch, mb.PALETTE[name], f"{name}: '{ch}' has no palette entry")

    def test_map_uses_every_tile(self):
        used = Counter(mb.tile_at(x, y) for y in range(mb.H) for x in range(mb.W))
        self.assertEqual(set(used), set(mb.TILES))

    def test_noise_wraps_without_a_seam(self):
        for y in range(mb.H):
            self.assertAlmostEqual(mb.noise(0, y, 7), mb.noise(mb.W, y, 7), places=9)
        for x in range(mb.W):
            self.assertAlmostEqual(mb.noise(x, 0, 99), mb.noise(x, mb.H, 99), places=9)


class Svg(unittest.TestCase):
    def test_overworld_size_strength_and_weight(self):
        svg = mb.overworld_svg()
        self.assertIn('width="320" height="208"', svg)
        self.assertIn('<g opacity="0.07">', svg)
        self.assertLess(len(svg.encode()), 100_000)
        self.assertEqual(len(re.findall(r"<use ", svg)), mb.W * mb.H)

    def test_output_is_deterministic(self):
        self.assertEqual(mb.overworld_svg(), mb.overworld_svg())

    def test_favicon_is_an_opaque_water_tile(self):
        svg = mb.favicon_svg()
        self.assertIn('viewBox="0 0 8 8"', svg)
        self.assertIn('fill="#2f5f78"', svg)
        self.assertNotIn("fill-opacity", svg)


if __name__ == "__main__":
    unittest.main()
