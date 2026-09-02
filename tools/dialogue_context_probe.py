#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
import time
from pathlib import Path
from typing import Any

from dialogue_stream_probe import runtime_layout
from ppsspp_debug import PPSSPPDebugger


ROOT = Path(__file__).resolve().parents[1]
# hle.module.list reports the loaded module at 0x08804000.  Debugger probes
# therefore use offsets relative to that module address, not ELF virtual
# addresses (whose .text section itself starts at 0x4000).
WALKER_MODULE_OFFSET = 0x00017E1C
WALKER_PROLOGUE = struct.pack("<II", 0x27BDfe90, 0xAFBF0164)
LOG_RE = re.compile(
    r"BOKU_CONTEXT\s+pc=([0-9a-f]+)\s+ra=([0-9a-f]+)\s+"
    r"a0=([0-9a-f]+)\s+a1=([0-9a-f]+)\s+a2=([0-9a-f]+)\s+a3=([0-9a-f]+)",
    re.IGNORECASE,
)


def read_raw_stream(session: PPSSPPDebugger, address: int, maximum: int = 4096) -> bytes:
    data = session.read(address, maximum)
    offset = 0
    while offset + 2 <= len(data):
        word = struct.unpack_from("<H", data, offset)[0]
        offset += 2
        if word in (0x8000, 0xFFFF):
            return data[:offset]
        if word == 0x8002:
            if offset + 2 > len(data):
                break
            offset += 2
    raise RuntimeError(f"no dialogue terminator within {maximum} bytes at 0x{address:08X}")


def record_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {key: record.get(key) for key in (
        "script", "pack_index", "pack_member", "dialog_id", "block_index",
        "element_index", "text_offset", "key", "text",
    )}


def capture_from_event(
    session: PPSSPPDebugger,
    event: dict[str, Any],
    by_raw: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    match = LOG_RE.search(str(event.get("message") or ""))
    if match is None:
        return None
    pc, ra, a0, a1, a2, a3 = (int(value, 16) for value in match.groups())
    if not (0x08000000 <= a1 < 0x0E000000):
        return None
    stream_pointer = struct.unpack("<I", session.read(a1 + 0x54, 4))[0]
    if not (0x08000000 <= stream_pointer < 0x0E000000):
        return None
    raw = read_raw_stream(session, stream_pointer)
    matches = by_raw.get(raw.hex().upper(), [])
    return {
        "event": event,
        "registers": {name: f"0x{value:08X}" for name, value in (
            ("pc", pc), ("ra", ra), ("a0", a0), ("a1", a1), ("a2", a2), ("a3", a3),
        )},
        "textbox_object": f"0x{a1:08X}",
        "stream_pointer": f"0x{stream_pointer:08X}",
        "raw_hex": raw.hex().upper(),
        "object_hex": session.read(a1, 0xC0).hex().upper(),
        "matching_records": [record_summary(item) for item in matches],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture structural context at the verified whole-dialogue walker")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", type=Path, default=ROOT / "analysis/debugger/dialogue-context.json")
    args = parser.parse_args()

    records = json.loads((ROOT / "data/es/dialogue.json").read_text(encoding="utf-8"))
    by_raw: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_raw.setdefault(record["raw_hex"].upper(), []).append(record)

    session = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    address: int | None = None
    report: dict[str, Any] = {}
    try:
        report["game_status"] = session.request("game.status")
        modules = session.request("hle.module.list")
        load_bias, _, _ = runtime_layout(modules)
        address = load_bias + WALKER_MODULE_OFFSET
        actual = session.read(address, len(WALKER_PROLOGUE))
        report["walker"] = {
            "address": f"0x{address:08X}",
            "expected": WALKER_PROLOGUE.hex().upper(),
            "actual": actual.hex().upper(),
        }
        if actual != WALKER_PROLOGUE:
            raise RuntimeError("whole-dialogue walker signature mismatch")

        input("Leave the current textbox visible and press ENTER to capture it as the baseline: ")
        session.request(
            "cpu.breakpoint.add", address=address, enabled=False, log=True,
            logFormat=(
                "BOKU_CONTEXT pc={pc:x} ra={ra:x} a0={a0:x} a1={a1:x} "
                "a2={a2:x} a3={a3:x} sp={sp:x}"
            ),
        )
        print("Capturing the currently visible stream as the baseline...")
        baseline_deadline = time.monotonic() + min(10.0, args.timeout)
        baseline = None
        while time.monotonic() < baseline_deadline and baseline is None:
            event = session.wait_event(
                {"log"}, baseline_deadline - time.monotonic(),
                predicate=lambda item: "BOKU_CONTEXT" in str(item.get("message") or ""),
            )
            baseline = capture_from_event(session, event, by_raw)
        if baseline is None:
            raise TimeoutError("the visible textbox did not reach the whole-dialogue walker")
        report["baseline"] = baseline
        print(
            f"BASELINE CAPTURED at {baseline['stream_pointer']} "
            f"({len(baseline['matching_records'])} structural match(es))."
        )
        print("ARMED (log-only). Advance dialogue normally until the next text stream appears.")
        print("A multi-page textbox may require more than one advance; repeated baseline draws are ignored.")

        deadline = time.monotonic() + args.timeout
        captured = None
        ignored_baseline_events = 0
        while time.monotonic() < deadline:
            event = session.wait_event(
                {"log"}, deadline - time.monotonic(),
                predicate=lambda item: "BOKU_CONTEXT" in str(item.get("message") or ""),
            )
            candidate = capture_from_event(session, event, by_raw)
            if candidate is None:
                continue
            if candidate["raw_hex"] == baseline["raw_hex"]:
                ignored_baseline_events += 1
                continue
            captured = candidate
            break
        if captured is None:
            raise TimeoutError("no valid whole-dialogue walker event before timeout")
        report["capture"] = captured
        report["ignored_baseline_events"] = ignored_baseline_events
        report["result"] = "captured"
        print(f"Captured {len(captured['matching_records'])} structural match(es).")
    except Exception as exc:
        report["result"] = "error"
        report["error"] = str(exc)
        raise
    finally:
        if address is not None:
            try:
                session.request("cpu.breakpoint.remove", address=address)
            except Exception:
                pass
        session.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
