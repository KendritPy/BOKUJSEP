import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dialogue_context_probe import (
    LOG_RE, WALKER_MODULE_OFFSET, WALKER_PROLOGUE, capture_from_event, read_raw_stream,
)


class FakeSession:
    def __init__(self, data):
        self.data = data

    def read(self, address, size):
        if address == 0x08929CA4 + 0x54:
            return struct.pack("<I", 0x0D751EF8)
        if address == 0x0D751EF8:
            return self.data[:size] + bytes(max(0, size - len(self.data)))
        return self.data[:size] + bytes(max(0, size - len(self.data)))


class DialogueContextProbeTests(unittest.TestCase):
    def test_module_relative_walker_address_and_signature(self):
        self.assertEqual(0x08804000 + WALKER_MODULE_OFFSET, 0x0881BE1C)
        self.assertEqual(WALKER_PROLOGUE.hex().upper(), "90FEBD276401BFAF")

    def test_log_parser(self):
        match = LOG_RE.search("BOKU_CONTEXT pc=881be1c ra=881aaaa a0=1 a1=8929ca4 a2=2 a3=3")
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(4), 16), 0x08929CA4)

    def test_stream_reader_keeps_page_guard_and_stops_at_real_terminator(self):
        words = (0x12, 0x8002, 0x44, 0, 0x33, 0x8000, 0x99)
        raw = b"".join(struct.pack("<H", word) for word in words)
        self.assertEqual(read_raw_stream(FakeSession(raw), 0x1000), raw[:-2])

    def test_capture_reads_object_stream_and_matches_raw(self):
        raw = struct.pack("<HH", 0x12, 0x8000)
        event = {"message": "BOKU_CONTEXT pc=881be1c ra=881aea0 a0=1 a1=8929ca4 a2=2 a3=3"}
        capture = capture_from_event(FakeSession(raw), event, {raw.hex().upper(): [{"script": "G2a.bin"}]})
        self.assertEqual(capture["stream_pointer"], "0x0D751EF8")
        self.assertEqual(capture["matching_records"][0]["script"], "G2a.bin")


if __name__ == "__main__":
    unittest.main()
