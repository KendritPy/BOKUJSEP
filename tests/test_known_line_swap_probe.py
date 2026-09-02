from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from known_line_swap_probe import load_atlas, load_code_patches, load_pair, locate_unique  # noqa: E402


class KnownLineSwapProbeTests(unittest.TestCase):
    def test_pair_is_identity_checked_and_fits(self) -> None:
        es_raw, jp_raw, pair = load_pair()
        self.assertEqual(pair["id"], "dlg_7fee236eb46522b8")
        self.assertLessEqual(len(jp_raw), len(es_raw))
        self.assertTrue(es_raw.endswith(b"\x00\x80"))
        self.assertTrue(jp_raw.endswith(b"\x00\x80"))

    def test_unique_locator(self) -> None:
        self.assertEqual(locate_unique(b"xxABCyy", b"ABC", 0x1000), 0x1002)
        with self.assertRaises(RuntimeError):
            locate_unique(b"ABCABC", b"ABC", 0x1000)

    def test_only_atlas_zero_differs(self) -> None:
        jp_zero = load_atlas("jp", 0)
        es_zero = load_atlas("es", 0)
        self.assertEqual(len(jp_zero), len(es_zero))
        self.assertNotEqual(jp_zero, es_zero)
        self.assertEqual(load_atlas("jp", 1), load_atlas("es", 1))

    def test_text_walker_has_seven_differences_but_one_width_patch(self) -> None:
        patches = load_code_patches(width_only=False)
        self.assertEqual(len(patches), 7)
        self.assertEqual(
            [address for address, _es, _jp in patches],
            [0x0881BF60, 0x0881BF84, 0x0881BF98, 0x0881C240,
             0x0881C244, 0x0881C29C, 0x0881C2A4],
        )
        width_patch = load_code_patches()
        self.assertEqual([address for address, _es, _jp in width_patch], [0x0891B5D4])
        self.assertEqual(int.from_bytes(width_patch[0][1], "little"), 0x80B60000)
        self.assertEqual(int.from_bytes(width_patch[0][2], "little"), 0x24160010)


if __name__ == "__main__":
    unittest.main()
