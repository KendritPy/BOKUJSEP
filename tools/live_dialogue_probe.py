#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from ppsspp_debug import PPSSPPDebugger


ROOT = Path(__file__).resolve().parents[1]
RAM_BASE = 0x08000000
RAM_SIZE = 0x02000000
CHUNK_SIZE = 0x00100000
CONTROL_WORDS = {0x0000, 0x8000, 0x8001, 0x8002, 0xFFFF}
TOKEN_RE = re.compile(r"\{[^}]*\}")


def load_records(path: Path) -> list[dict[str, Any]]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"expected a JSON list in {path}")
    return records


def read_ram(debugger: PPSSPPDebugger) -> bytes:
    data = bytearray()
    for offset in range(0, RAM_SIZE, CHUNK_SIZE):
        size = min(CHUNK_SIZE, RAM_SIZE - offset)
        data.extend(debugger.read(RAM_BASE + offset, size))
        print(f"read RAM 0x{offset + size:08X}/0x{RAM_SIZE:08X}", end="\r")
    print()
    return bytes(data)


def raw_bytes(record: dict[str, Any]) -> bytes:
    value = record.get("raw_hex") or ""
    try:
        return bytes.fromhex(value)
    except ValueError:
        return b""


def trim_raw(raw: bytes) -> bytes:
    while len(raw) >= 2 and raw[-2:] in (b"\x00\x00", b"\xff\xff", b"\x00\x80"):
        raw = raw[:-2]
    return raw[: len(raw) // 2 * 2]


def words(raw: bytes) -> list[int]:
    clean = trim_raw(raw)
    return [value for (value,) in struct.iter_unpack("<H", clean)]


def best_anchor(raw: bytes, preferred_words: int = 6) -> bytes:
    """Pick a text-heavy interior window instead of blindly using the prefix."""
    values = words(raw)
    if len(values) < 4:
        return b""
    width = min(preferred_words, len(values))
    best: tuple[tuple[int, int, int, int], int] | None = None
    for start in range(0, len(values) - width + 1):
        window = values[start:start + width]
        controls = sum(value in CONTROL_WORDS for value in window)
        text_words = width - controls
        distinct = len(set(value for value in window if value not in CONTROL_WORDS))
        score = (text_words, distinct, -controls, -start)
        if best is None or score > best[0]:
            best = (score, start)
    if best is None or best[0][0] < 4:
        return b""
    start = best[1] * 2
    return trim_raw(raw)[start:start + width * 2]


def candidate_windows(raw: bytes, width_words: int = 4) -> list[tuple[int, bytes]]:
    """All text-like aligned windows for one targeted extracted record."""
    values = words(raw)
    if len(values) < width_words:
        return []
    clean = trim_raw(raw)
    result: list[tuple[int, bytes]] = []
    seen: set[bytes] = set()
    for start in range(0, len(values) - width_words + 1):
        window_words = values[start:start + width_words]
        if any(value in CONTROL_WORDS for value in window_words):
            continue
        if len(set(window_words)) < 2:
            continue
        window = clean[start * 2:(start + width_words) * 2]
        if window in seen:
            continue
        seen.add(window)
        result.append((start * 2, window))
    return result


def normalize_text(value: str) -> str:
    value = TOKEN_RE.sub(" ", value or "")
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\r", " ").replace("\n", " ")
    return " ".join(value.split()).casefold()


def record_label(record: dict[str, Any]) -> str:
    fields = []
    for key in ("script", "pack_index", "pack_member", "dialog_id", "block_index", "element_index", "key"):
        value = record.get(key)
        if value is not None:
            fields.append(f"{key}={value}")
    return " ".join(fields)


def find_all(haystack: bytes, needle: bytes, limit: int = 64) -> list[int]:
    if not needle:
        return []
    result = []
    start = 0
    while len(result) < limit:
        found = haystack.find(needle, start)
        if found < 0:
            break
        result.append(RAM_BASE + found)
        start = found + 1
    return result


def literal_searches(ram: bytes, text: str) -> list[dict[str, Any]]:
    results = []
    for encoding in ("utf-8", "latin-1", "utf-16le", "utf-16be"):
        try:
            payload = text.encode(encoding)
        except UnicodeEncodeError:
            continue
        hits = find_all(ram, payload)
        results.append({
            "encoding": encoding,
            "bytes": payload.hex().upper(),
            "hits": [f"0x{address:08X}" for address in hits],
        })
    return results


def targeted_record_hits(ram: bytes, raw: bytes) -> list[dict[str, Any]]:
    hits = []
    for offset, window in candidate_windows(raw):
        addresses = find_all(ram, window, limit=16)
        if not addresses:
            continue
        hits.append({
            "raw_offset": offset,
            "window": window.hex().upper(),
            "addresses": [f"0x{address:08X}" for address in addresses],
        })
    return hits


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read PPSSPP RAM and locate the live Spanish dialogue representation."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--dialogue",
        type=Path,
        default=ROOT / "data" / "es" / "dialogue.json",
        help="extracted dialogue JSON to match (default: ES)",
    )
    parser.add_argument(
        "--text",
        default="La cena que he preparado hoy era",
        help="visible text fragment used to identify the canonical extracted record",
    )
    parser.add_argument("--limit", type=int, default=30, help="maximum general resident matches")
    parser.add_argument("--json", type=Path, help="optional JSON report path")
    args = parser.parse_args()

    if not args.dialogue.is_file():
        raise SystemExit(f"missing {args.dialogue}; run scripts/pipeline.ps1 first")

    records = load_records(args.dialogue)
    raws = [raw_bytes(record) for record in records]

    query = normalize_text(args.text)
    text_candidates = []
    if query:
        for index, record in enumerate(records):
            decoded = normalize_text(str(record.get("text") or ""))
            if query in decoded:
                text_candidates.append(index)

    anchor_records: dict[bytes, list[int]] = defaultdict(list)
    for index, raw in enumerate(raws):
        anchor = best_anchor(raw)
        if anchor:
            anchor_records[anchor].append(index)

    anchors = sorted(anchor_records, key=lambda value: (-len(value), value))
    if not anchors:
        raise SystemExit("no usable dialogue anchors were found")
    matcher = re.compile(b"|".join(re.escape(anchor) for anchor in anchors))

    debugger = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    try:
        status = debugger.request("game.status")
        print(f"game.status: {status}")
        ram = read_ram(debugger)
    finally:
        debugger.close()

    literal = literal_searches(ram, args.text)
    if any(item["hits"] for item in literal):
        print("Literal text representation found in RAM:")
        for item in literal:
            if item["hits"]:
                print(f"  {item['encoding']}: {', '.join(item['hits'])}")
    else:
        print("No literal UTF-8/Latin-1/UTF-16 copy of the visible phrase was found.")

    print(f"Offline text query: {args.text!r}")
    print(f"Matching extracted records after NFKC normalization: {len(text_candidates)}")
    targeted = []
    for index in text_candidates[:20]:
        record = records[index]
        raw = raws[index]
        window_hits = targeted_record_hits(ram, raw)
        item = {
            "record_index": index,
            "label": record_label(record),
            "text": record.get("text"),
            "raw_hex": raw.hex().upper(),
            "raw_bytes": len(raw),
            "window_hits": window_hits,
        }
        targeted.append(item)
        print(f"  record {index}: {record_label(record)} raw={len(raw)}B")
        if record.get("text"):
            print(f"    decoded: {record.get('text')}")
        if window_hits:
            count = sum(len(hit["addresses"]) for hit in window_hits)
            print(f"    RAM interior-window hits: {count}")
        else:
            print("    RAM interior-window hits: 0")

    matches: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for hit in matcher.finditer(ram):
        anchor = hit.group(0)
        address = RAM_BASE + hit.start()
        for index in anchor_records[anchor]:
            key = (index, address)
            if key in seen:
                continue
            seen.add(key)
            raw = raws[index]
            record = records[index]
            matches.append({
                "address": f"0x{address:08X}",
                "anchor_bytes": len(anchor),
                "raw_bytes": len(raw),
                "record_index": index,
                "script": record.get("script"),
                "pack_index": record.get("pack_index"),
                "pack_member": record.get("pack_member"),
                "dialog_id": record.get("dialog_id"),
                "block_index": record.get("block_index"),
                "element_index": record.get("element_index"),
                "key": record.get("key"),
                "text": record.get("text"),
            })

    matches.sort(key=lambda item: (
        -int(item["raw_bytes"]),
        -int(item["anchor_bytes"]),
        item["address"],
    ))
    shown = matches[: max(0, args.limit)]

    if not shown:
        print("No best-interior anchors from the extracted dialogue database were found in PSP RAM.")
    else:
        print(f"Found {len(matches)} general resident dialogue candidates; showing {len(shown)} strongest:")
        for number, item in enumerate(shown, 1):
            print(f"[{number:02d}] {item['address']} anchor={item['anchor_bytes']}B raw={item['raw_bytes']}B")
            print(f"     {record_label(records[item['record_index']])}")
            if item.get("text"):
                print(f"     {item['text']}")

    report = {
        "dialogue": str(args.dialogue),
        "records": len(records),
        "query_text": args.text,
        "normalized_query": query,
        "text_candidate_count": len(text_candidates),
        "text_candidates": targeted,
        "literal_searches": literal,
        "unique_anchors": len(anchors),
        "matches_total": len(matches),
        "matches": shown,
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.json}")


if __name__ == "__main__":
    main()
