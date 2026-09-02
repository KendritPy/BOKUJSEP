#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MAGIC = b"BLT1"
VERSION = 2
HEADER = struct.Struct("<4sIIII32s")
ENTRY = struct.Struct("<QIIIIIIHHHHH")
FLAG_AMBIGUOUS_RAW = 1 << 0
FLAG_PAGE_COUNT_MISMATCH = 1 << 1
CONTEXT_SIZE = 256


def identity_hash(item: dict[str, Any]) -> int:
    identity = "|".join(str(item.get(key, "")) for key in (
        "script", "pack_index", "pack_member", "dialog_id",
        "block_index", "element_index", "key",
    ))
    return int.from_bytes(hashlib.sha256(identity.encode("utf-8")).digest()[:8], "little")


@dataclass(frozen=True)
class BlobEntry:
    identity: int
    es_offset: int
    jp_offset: int
    context_offset: int
    es_text_offset: int
    es_size: int
    jp_size: int
    context_size: int
    dialog_id: int
    block_index: int
    element_index: int
    flags: int


def page_offsets(raw: bytes) -> list[int]:
    offsets = [0]
    for offset in range(0, len(raw) - 5, 2):
        if struct.unpack_from("<H", raw, offset)[0] == 0x8002:
            if struct.unpack_from("<H", raw, offset + 4)[0] == 0:
                offsets.append(offset + 4)
    return offsets


def build_blob(
    pairs: list[dict[str, Any]],
    context_for: Any | None = None,
) -> tuple[bytes, dict[str, int]]:
    payload = bytearray()
    stream_offsets: dict[bytes, int] = {}

    def intern(raw: bytes) -> int:
        offset = stream_offsets.get(raw)
        if offset is None:
            offset = len(payload)
            stream_offsets[raw] = offset
            payload.extend(raw)
        return offset

    grouped: dict[bytes, set[bytes]] = {}
    decoded: list[tuple[dict[str, Any], bytes, bytes]] = []
    for pair in pairs:
        es_raw = bytes.fromhex(pair["es"]["raw"])
        jp_raw = bytes.fromhex(pair["jp"]["raw"])
        if not es_raw or not jp_raw or len(es_raw) > 0xFFFF or len(jp_raw) > 0xFFFF:
            raise ValueError(f"invalid stream size for {pair.get('id')}")
        grouped.setdefault(es_raw, set()).add(jp_raw)
        decoded.append((pair, es_raw, jp_raw))

    entries: list[BlobEntry] = []
    ambiguous_records = 0
    page_mismatch_records = 0
    for pair, es_raw, jp_raw in decoded:
        ambiguous = len(grouped[es_raw]) > 1
        ambiguous_records += int(ambiguous)
        page_mismatch = len(page_offsets(es_raw)) != len(page_offsets(jp_raw))
        page_mismatch_records += int(page_mismatch)
        context = bytes(context_for(pair)) if context_for is not None else b""
        if len(context) > 0xFFFF:
            raise ValueError(f"context signature too large for {pair.get('id')}")
        entries.append(BlobEntry(
            identity=identity_hash(pair),
            es_offset=intern(es_raw),
            jp_offset=intern(jp_raw),
            context_offset=intern(context),
            es_text_offset=int(pair["es"]["text_offset"]),
            es_size=len(es_raw),
            jp_size=len(jp_raw),
            context_size=len(context),
            dialog_id=int(pair["dialog_id"]),
            block_index=int(pair["block_index"]),
            element_index=int(pair["element_index"]),
            flags=(FLAG_AMBIGUOUS_RAW if ambiguous else 0)
            | (FLAG_PAGE_COUNT_MISMATCH if page_mismatch else 0),
        ))

    entries.sort(key=lambda item: (item.identity, item.dialog_id, item.block_index, item.element_index))
    table = b"".join(ENTRY.pack(
        item.identity, item.es_offset, item.jp_offset, item.context_offset,
        item.es_text_offset, item.es_size, item.jp_size, item.context_size,
        item.dialog_id, item.block_index, item.element_index, item.flags,
    ) for item in entries)
    digest = hashlib.sha256(table + payload).digest()
    payload_offset = HEADER.size + len(table)
    header = HEADER.pack(MAGIC, VERSION, len(entries), ENTRY.size, payload_offset, digest)
    stats = {
        "records": len(entries),
        "unambiguous_records": len(entries) - ambiguous_records,
        "ambiguous_records": ambiguous_records,
        "page_mismatch_records": page_mismatch_records,
        "unique_streams": len(stream_offsets),
        "payload_bytes": len(payload),
        "blob_bytes": len(header) + len(table) + len(payload),
    }
    return header + table + payload, stats


def load_context_provider(root: Path):
    source = root / "external/boku-korean-tools/tools/boku_tools.py"
    spec = importlib.util.spec_from_file_location("boku_tools_blob", source)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    cache: dict[tuple[str, int], bytes] = {}

    def context_for(pair: dict[str, Any]) -> bytes:
        key = (str(pair["script"]), int(pair["pack_index"]))
        if key not in cache:
            script = (root / "extracted/es/cdimg/map/gz" / key[0]).read_bytes()
            member = module.parse_pack(script, with_names=True)[key[1]][1]
            payload = module.gzip_payload(member)
            dialogs = module.parse_pack(payload, with_names=False)[1][1]
            cache[key] = dialogs[:CONTEXT_SIZE]
        return cache[key]

    return context_for


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the immutable structural JP/ES dialogue blob")
    parser.add_argument("--pairs", type=Path, default=ROOT / "data/bilingual/dialogue_pairs.json")
    parser.add_argument("--output", type=Path, default=ROOT / "build/generated/dialogue_blob.bin")
    parser.add_argument("--report", type=Path, default=ROOT / "analysis/diffs/dialogue_blob.json")
    args = parser.parse_args()
    pairs = json.loads(args.pairs.read_text(encoding="utf-8"))
    blob, stats = build_blob(pairs, load_context_provider(ROOT))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(blob)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(stats)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
