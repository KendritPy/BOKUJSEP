import hashlib
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_dialogue_blob import (
    ENTRY, FLAG_AMBIGUOUS_RAW, FLAG_PAGE_COUNT_MISMATCH, HEADER, MAGIC, VERSION,
    build_blob, identity_hash, page_offsets,
)


def pair(key: str, es: str, jp: str, block: int = 1):
    return {
        "id": "unused", "script": "A0.bin", "pack_index": 0,
        "pack_member": "M_A01000.bin.gz", "dialog_id": 4,
        "block_index": block, "element_index": 4, "key": key,
        "es": {"raw": es, "text_offset": 0x120},
        "jp": {"raw": jp, "text_offset": 0x100},
    }


class DialogueBlobTests(unittest.TestCase):
    def test_blob_is_deterministic_and_digest_covers_table_and_payload(self):
        pairs = [pair("a", "01000080", "02000080")]
        left, stats = build_blob(pairs)
        right, _ = build_blob(pairs)
        self.assertEqual(left, right)
        magic, version, count, entry_size, payload_offset, digest = HEADER.unpack_from(left)
        self.assertEqual((magic, version, count, entry_size), (MAGIC, VERSION, 1, ENTRY.size))
        self.assertEqual(digest, hashlib.sha256(left[HEADER.size:]).digest())
        self.assertEqual(payload_offset, HEADER.size + ENTRY.size)
        self.assertEqual(stats["unambiguous_records"], 1)

    def test_conflicting_identical_spanish_streams_are_flagged(self):
        blob, stats = build_blob([
            pair("a", "01000080", "02000080", 1),
            pair("b", "01000080", "03000080", 2),
        ])
        flags = []
        for index in range(2):
            values = ENTRY.unpack_from(blob, HEADER.size + index * ENTRY.size)
            flags.append(values[-1])
        self.assertEqual(flags, [FLAG_AMBIGUOUS_RAW, FLAG_AMBIGUOUS_RAW])
        self.assertEqual(stats["ambiguous_records"], 2)

    def test_context_and_page_mismatch_are_encoded(self):
        item = pair("a", "01000280010000000080", "02000080")
        blob, stats = build_blob([item], lambda _item: b"context")
        values = ENTRY.unpack_from(blob, HEADER.size)
        context_offset, context_size, flags = values[3], values[7], values[-1]
        payload_offset = HEADER.unpack_from(blob)[4]
        self.assertEqual(blob[payload_offset + context_offset:payload_offset + context_offset + context_size], b"context")
        self.assertEqual(flags, FLAG_PAGE_COUNT_MISMATCH)
        self.assertEqual(stats["page_mismatch_records"], 1)

    def test_page_offsets_point_at_zero_guard(self):
        raw = struct.pack("<HHHHH", 1, 0x8002, 0x2D, 0, 0x8000)
        self.assertEqual(page_offsets(raw), [0, 6])

    def test_identity_includes_structural_position(self):
        self.assertNotEqual(identity_hash(pair("a", "01", "02", 1)), identity_hash(pair("a", "01", "02", 2)))


if __name__ == "__main__":
    unittest.main()
