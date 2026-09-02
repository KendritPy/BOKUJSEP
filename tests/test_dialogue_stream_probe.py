from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dialogue_stream_probe import expected_words, parse_words, runtime_layout  # noqa: E402


class DialogueStreamProbeTests(unittest.TestCase):
    def test_signature_is_move_then_relocated_spanish_call(self) -> None:
        self.assertEqual(expected_words(0x08919BF0), (0x02602021, 0x0E2466FC))

    def test_runtime_layout_accounts_for_elf_text_address(self) -> None:
        modules = {"modules": [{"name": "bnp", "address": 0x08804000}]}
        self.assertEqual(runtime_layout(modules), (0x08804000, 0x08843070, 0x08919BF0))

    def test_parse_words_stops_at_raw_terminator(self) -> None:
        data = struct.pack("<5H", 0x12, 0x8002, 0x34, 0x0000, 0x8000)
        words, terminated = parse_words(data + b"ignored")
        self.assertTrue(terminated)
        self.assertEqual(words, [0x12, 0x8002, 0x34, 0x0000, 0x8000])


if __name__ == "__main__":
    unittest.main()
