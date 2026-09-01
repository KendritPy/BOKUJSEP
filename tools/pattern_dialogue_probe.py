#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

from ppsspp_debug import PPSSPPDebugger


ROOT = Path(__file__).resolve().parents[1]
RAM_BASE = 0x08000000
RAM_SIZE = 0x02000000
CHUNK_SIZE = 0x00100000


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("\r", " ").replace("\n", " ")
    return " ".join(value.split()).casefold()


def read_ram(debugger: PPSSPPDebugger) -> bytes:
    data = bytearray()
    for offset in range(0, RAM_SIZE, CHUNK_SIZE):
        size = min(CHUNK_SIZE, RAM_SIZE - offset)
        data.extend(debugger.read(RAM_BASE + offset, size))
        print(f"read RAM 0x{offset + size:08X}/0x{RAM_SIZE:08X}", end="\r")
    print()
    return bytes(data)


def wait_for_cpu_state(
    debugger: PPSSPPDebugger,
    stepping: bool,
    timeout: float = 5.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = debugger.request("cpu.status")
        if bool(last.get("stepping")) == stepping:
            return last
        time.sleep(0.03)
    wanted = "stepping" if stepping else "running"
    raise RuntimeError(
        f"PPSSPP CPU did not become {wanted} within {timeout:.1f}s; last cpu.status={last}"
    )


def stable_ram_snapshot(
    debugger: PPSSPPDebugger,
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    """Take a coherent RAM image while CPU stepping, then leave the game running.

    This probe is an interactive one-shot diagnostic, so an already-stepping CPU
    is treated as a stale/debug pause (not as UI pause state) and is resumed when
    the snapshot finishes. This also recovers from the older probe bug that could
    leave the CPU stepping after a timeout.
    """
    game_status = debugger.request("game.status")
    cpu_status = debugger.request("cpu.status")
    print(f"game.status before snapshot: {game_status}")
    print(f"cpu.status before snapshot:  {cpu_status}")

    already_stepping = bool(cpu_status.get("stepping"))
    if already_stepping:
        print("CPU is already stepping; using the existing debug pause for this snapshot.")
    else:
        print("Pausing PSP CPU for a coherent RAM snapshot...")
        debugger.fire("cpu.stepping")

    snapshot_error: BaseException | None = None
    ram = b""
    try:
        wait_for_cpu_state(debugger, True)
        print("CPU stepping confirmed.")
        ram = read_ram(debugger)
    except BaseException as error:
        snapshot_error = error
    finally:
        # This diagnostic always leaves the game running. In particular, this
        # repairs the stale stepping state an older failed probe may have left.
        try:
            current = debugger.request("cpu.status")
            if current.get("stepping"):
                print("Resuming PSP CPU...")
                debugger.fire("cpu.resume")
                wait_for_cpu_state(debugger, False)
                print("CPU running confirmed.")
            else:
                print("CPU is already running.")
        except BaseException as resume_error:
            if snapshot_error is None:
                raise
            print(f"WARNING: snapshot failed and automatic resume also failed: {resume_error}")

    if snapshot_error is not None:
        raise snapshot_error
    print("RAM snapshot complete; PPSSPP resumed.")
    return game_status, cpu_status, ram


def find_all(haystack: bytes, needle: bytes, limit: int = 64) -> list[int]:
    if not needle:
        return []
    result: list[int] = []
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
            "hits": [f"0x{address:08X}" for address in hits],
        })
    return results


def equality_regex(text: str, symbol_bytes: int) -> tuple[re.Pattern[bytes], dict[str, str]]:
    """Match an unknown fixed-width encoding using only character equality.

    Example: ABBA becomes capture(A), capture(B), backref(B), backref(A).
    No knowledge of the game's character table is required. New characters are
    constrained to differ from all earlier captures, greatly reducing false hits.
    """
    if not text:
        raise ValueError("text pattern cannot be empty")
    names: dict[str, str] = {}
    name_to_char: dict[str, str] = {}
    pieces: list[bytes] = []

    for char in text:
        if char in names:
            pieces.append(f"(?P={names[char]})".encode("ascii"))
            continue

        name = f"c{len(names)}"
        if names:
            alternatives = b"|".join(
                f"(?P={existing})".encode("ascii") for existing in names.values()
            )
            pieces.append(b"(?!(?:" + alternatives + b"))")
        pieces.append(f"(?P<{name}>.{{{symbol_bytes}}})".encode("ascii"))
        names[char] = name
        name_to_char[name] = char

    return re.compile(b"".join(pieces), re.DOTALL), name_to_char


def format_char(char: str) -> str:
    if char == " ":
        return "<space>"
    if char == "\t":
        return "<tab>"
    return char


def equality_search(ram: bytes, text: str, symbol_bytes: int, limit: int = 32) -> list[dict[str, Any]]:
    pattern, name_to_char = equality_regex(text, symbol_bytes)
    hits: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(ram) and len(hits) < limit:
        match = pattern.search(ram, cursor)
        if match is None:
            break

        address = RAM_BASE + match.start()
        # A 16-bit glyph stream should be word aligned in PSP RAM. Advance by
        # one byte after a rejected shifted match so an overlapping aligned
        # candidate at the next byte is still considered.
        if symbol_bytes == 2 and (address & 1):
            cursor = match.start() + 1
            continue

        mapping: dict[str, str] = {}
        for name, char in name_to_char.items():
            value = match.group(name)
            if symbol_bytes == 2:
                numeric = int.from_bytes(value, "little")
                mapping[format_char(char)] = f"0x{numeric:04X}"
            else:
                mapping[format_char(char)] = f"0x{value[0]:02X}"
        hits.append({
            "address": f"0x{address:08X}",
            "symbol_bytes": symbol_bytes,
            "byte_length": match.end() - match.start(),
            "mapping": mapping,
            "raw_hex": match.group(0).hex().upper(),
        })
        cursor = match.start() + 1
    return hits


def decoded_database_info(path: Path, text: str) -> dict[str, Any]:
    """Informational only: ES text currently uses the JP table, so zero is expected."""
    if not path.is_file():
        return {"available": False}
    records = json.loads(path.read_text(encoding="utf-8"))
    query = normalize_text(text)
    indices = []
    for index, record in enumerate(records):
        decoded = normalize_text(str(record.get("text") or ""))
        if query and query in decoded:
            indices.append(index)
    return {
        "available": True,
        "records": len(records),
        "decoded_matches": indices[:50],
        "warning": "ES decoded text is provisional because extraction currently uses the JP table; do not treat zero matches as extraction failure.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Locate visible Boku dialogue in PPSSPP RAM without knowing the Spanish character table."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--text",
        default="La cena que he preparado hoy era",
        help="exact visible phrase to locate; punctuation may be included when visible",
    )
    parser.add_argument(
        "--dialogue",
        type=Path,
        default=ROOT / "data" / "es" / "dialogue.json",
        help="optional extracted ES dialogue JSON, used only for diagnostics",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=ROOT / "analysis" / "debugger" / "pattern-dialogue.json",
    )
    parser.add_argument("--limit", type=int, default=32)
    args = parser.parse_args()

    db_info = decoded_database_info(args.dialogue, args.text)
    if db_info.get("available"):
        print(
            f"Decoded ES database: {db_info['records']} records; textual matches={len(db_info['decoded_matches'])}."
        )
        print("NOTE: ES decoding currently uses the JP table, so this textual count is diagnostic only.")

    debugger = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    try:
        game_status, cpu_status, ram = stable_ram_snapshot(debugger)
    finally:
        debugger.close()

    literal = literal_searches(ram, args.text)
    literal_count = sum(len(item["hits"]) for item in literal)
    print(f"Literal UTF/Latin representations: {literal_count} hit(s).")

    print("Searching equality pattern as one 16-bit code per visible character...")
    hits16 = equality_search(ram, args.text, 2, args.limit)
    print(f"16-bit equality-pattern candidates: {len(hits16)}")
    for index, hit in enumerate(hits16[:10], 1):
        print(f"  [{index:02d}] {hit['address']}  {hit['byte_length']} bytes")
        preview = ", ".join(f"{key}={value}" for key, value in list(hit["mapping"].items())[:12])
        print(f"       {preview}")

    print("Searching equality pattern as one 8-bit code per visible character...")
    hits8 = equality_search(ram, args.text, 1, args.limit)
    print(f"8-bit equality-pattern candidates: {len(hits8)}")
    for index, hit in enumerate(hits8[:10], 1):
        print(f"  [{index:02d}] {hit['address']}  {hit['byte_length']} bytes")
        preview = ", ".join(f"{key}={value}" for key, value in list(hit["mapping"].items())[:12])
        print(f"       {preview}")

    if not hits16 and not hits8:
        print("No fixed-width equality-pattern candidate was found.")
        print("That would point to a transformed/layout/glyph buffer rather than a simple encoded text stream.")
    else:
        print("Candidate(s) found. Next step is to validate them against another visible line and set read breakpoints.")

    report = {
        "query_text": args.text,
        "game_status_before_snapshot": game_status,
        "cpu_status_before_snapshot": cpu_status,
        "decoded_database": db_info,
        "literal_searches": literal,
        "equality_16bit": hits16,
        "equality_8bit": hits8,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.json}")


if __name__ == "__main__":
    main()
