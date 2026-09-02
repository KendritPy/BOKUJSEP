from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from compare_eboot import build_report  # noqa: E402


class EbootComparisonTests(unittest.TestCase):
    def test_real_pair_exposes_spanish_injected_region_and_edges(self) -> None:
        report = build_report(
            ROOT / "extracted/jp/iso/PSP_GAME/SYSDIR/BOOT.BIN",
            ROOT / "extracted/es/iso/PSP_GAME/SYSDIR/EBOOT.BIN",
        )
        injected = report["spanish_injected_region"]
        self.assertEqual(injected["size"], 0x7F00)
        self.assertEqual(injected["guest_start"], "0x08918FF0")
        edges = report["direct_text_edges_into_injected_region"]
        self.assertEqual(len(edges), 7)
        self.assertIn("0x08843074", {edge["source_guest"] for edge in edges})


if __name__ == "__main__":
    unittest.main()
