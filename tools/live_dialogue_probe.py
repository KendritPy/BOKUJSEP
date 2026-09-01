#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from ppsspp_debug import PPSSPPDebugger


ROOT = Path(__file__).resolve().parents[1]
RAM_BASE = 0x08000000
RAM_SIZE = 0x02000000
CHUNK_SIZE = 0x00100000


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


def useful_anchor(raw: bytes, minimum: int = 8, maximum: int = 16) -> bytes:
    """Return a short exact byte anchor, trimming common trailing terminators.

    We intentionally keep this format-agnostic: this is a RAM locator, not a
    decoder. Full raw equality is checked separately when possible.
    """
    while len(raw) >= 2 and raw[-2:] in (b"\x00\x00", b"\xff\xff"):
        raw = raw[:-2]
    if len(raw) < minimum:
        return b""
    return raw[: min(maximum, len(raw))]


def record_label(record: dict[str, Any]) -> str:
    fields = []
    for key in ("script", "pack_index", "pack_member", "dialog_id", "block_index", "element_index", "key"):
        value = record.get(key)
        if value is not None:
            fields.append(f"{key}={value}")
    return " ".join(fields)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read PPSSPP RAM once and identify extracted ES dialogue records resident in memory."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--dialogue",
        type=Path,
        default=ROOT / "data" / "es" / "dialogue.json",
        help="extracted dialogue JSON to match (default: ES)",
    )
    parser.add_argument("--limit", type=int, default=30, help="maximum reported matches")
    parser.add_argument("--json", type=Path, help="optional JSON report path")
    args = parser.parse_args()

    if not args.dialogue.is_file():
        raise SystemExit(f"missing {args.dialogue}; run scripts/pipeline.ps1 first")

    records = load_records(args.dialogue)
    anchor_records: dict[bytes, list[int]] = defaultdict(list)
    raws: list[bytes] = []
    for index, record in enumerate(records):
        raw = raw_bytes(record)
        raws.append(raw)
        anchor = useful_anchor(raw)
        if anchor:
            anchor_records[anchor].append(index)

    # Longer alternatives first prevents a short prefix from shadowing a
    # longer one in Python's leftmost-first regex engine.
    anchors = sorted(anchor_records, key=lambda value: (-len(value), value))
    if not anchors:
        raise SystemExit("no usable dialogue anchors were found")
    matcher = re.compile(b"|".join(re.escape(anchor) for anchor in anchors))

    debugger = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    try:
        status = debugger.request("game.status")
        print(f"game.status: {status.get('game', status.get('title', status.get('event', 'connected')))}")
        ram = read_ram(debugger)
    finally:
        debugger.close()

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
            exact = bool(raw) and ram[hit.start() : hit.start() + len(raw)] == raw
            record = records[index]
            matches.append({
                "address": f"0x{address:08X}",
                "exact_full_raw": exact,
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

    # Exact full records are strongest, then longer records/anchors. Resident
    # script archives may produce many weak matches; the visible line should
    # normally be among the strongest candidates, not blindly assumed #1.
    matches.sort(key=lambda item: (
        not item["exact_full_raw"],
        -int(item["raw_bytes"]),
        -int(item["anchor_bytes"]),
        item["address"],
    ))

    shown = matches[: max(0, args.limit)]
    if not shown:
        print("No extracted dialogue anchors were found in PSP RAM.")
        print("That is useful evidence: the active renderer may use a transformed/copied representation.")
    else:
        print(f"Found {len(matches)} resident dialogue candidates; showing {len(shown)} strongest:\n")
        for number, item in enumerate(shown, 1):
            strength = "FULL" if item["exact_full_raw"] else f"anchor {item['anchor_bytes']}B"
            print(f"[{number:02d}] {item['address']} {strength} raw={item['raw_bytes']}B")
            record = records[item["record_index"]]
            print(f"     {record_label(record)}")
            text = item.get("text")
            if text:
                print(f"     {text}")

    report = {
        "dialogue": str(args.dialogue),
        "records": len(records),
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
