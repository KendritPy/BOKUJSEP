from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dialogue_watch_event_probe import stepping_matches_memcheck  # noqa: E402


class SteppingMatchTests(unittest.TestCase):
    def test_matches_ppsspp_1_20_4_memory_breakpoint_event(self) -> None:
        event = {
            "event": "cpu.stepping",
            "pc": 0x08812340,
            "reason": "memory.breakpoint",
            "relatedAddress": 0x0892EBA4,
        }
        self.assertTrue(stepping_matches_memcheck(event, 0x0892EBA4, 2))

    def test_rejects_unrelated_stepping_event(self) -> None:
        event = {
            "event": "cpu.stepping",
            "reason": "ui.lost_focus",
            "relatedAddress": 0,
        }
        self.assertFalse(stepping_matches_memcheck(event, 0x0892EBA4, 2))

    def test_matches_newer_enriched_stepping_event(self) -> None:
        event = {
            "event": "cpu.stepping",
            "reason": "memory.breakpoint",
            "hit": {
                "kind": "memory",
                "address": 0x0892EBA4,
                "size": 2,
                "breakpoint": {"start": 0x0892EBA4, "end": 0x0892EBA6},
            },
        }
        self.assertTrue(stepping_matches_memcheck(event, 0x0892EBA4, 2))


if __name__ == "__main__":
    unittest.main()
