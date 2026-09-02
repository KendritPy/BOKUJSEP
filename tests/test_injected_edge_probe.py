from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from injected_edge_probe import EDGES, branch_word  # noqa: E402


class InjectedEdgeProbeTests(unittest.TestCase):
    def test_all_offline_edges_are_present(self) -> None:
        self.assertEqual(len(EDGES), 7)

    def test_relocated_jal_word(self) -> None:
        self.assertEqual(branch_word("jal", 0x08919BF0), 0x0E2466FC)

    def test_relocated_jump_word(self) -> None:
        self.assertEqual(branch_word("j", 0x0891A27C), 0x0A24689F)


if __name__ == "__main__":
    unittest.main()
