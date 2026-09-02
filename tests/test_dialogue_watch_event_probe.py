from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dialogue_watch_event_probe import memcheck_log_writer, stepping_matches_memcheck  # noqa: E402


class SteppingMatchTests(unittest.TestCase):
    def test_matches_ppsspp_1_20_4_memory_breakpoint_event(self) -> None:
        event = {
            "event": "cpu.stepping",
            "pc": 0x08812340,
            "reason": "memory.breakpoint",
            "relatedAddress": 0x0892EBA4,
        }
        self.assertTrue(stepping_matches_memcheck(event, 0x0892EBA4, 2))

    def test_extracts_exact_ppsspp_memcheck_log_writer(self) -> None:
        event = {
            "event": "log",
            "message": "CHK Write16(CPU) at 0892eba4 ((0892eba4)), PC=088a0e4c (fn)\n",
        }
        self.assertEqual(memcheck_log_writer(event, 0x0892EBA4, 2), 0x088A0E4C)

    def test_extracts_custom_register_trace_writer(self) -> None:
        event = {
            "event": "log",
            "message": "CHK Write16(CPU) at 0892eba4: BOKU_WATCH pc=088a0e4c a0=0892eb9c\n",
        }
        self.assertEqual(memcheck_log_writer(event, 0x0892EBA4, 2), 0x088A0E4C)

    def test_rejects_unrelated_memcheck_log(self) -> None:
        event = {
            "event": "log",
            "message": "CHK Write16(CPU) at 0892eba8 ((0892eba8)), PC=088a0e4c (fn)\n",
        }
        self.assertIsNone(memcheck_log_writer(event, 0x0892EBA4, 2))

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
