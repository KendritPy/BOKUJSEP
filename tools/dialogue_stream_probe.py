#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
import time
from pathlib import Path
from typing import Any

from ppsspp_debug import PPSSPPDebugger

ROOT = Path(__file__).resolve().parents[1]
GAME_MODULE = "bnp"
HOOK_ELF_ADDRESS = 0x0003F070
TARGET_ELF_ADDRESS = 0x00115BF0
MOVE_A0_S3 = 0x02602021
LOG_FORMAT = "BOKU_STREAM pc={pc:x} s3={s3:x} fp={fp:x} s1={s1:x} sp={sp:x} ra={ra:x}"
LOG_RE = re.compile(r"BOKU_STREAM\s+pc=([0-9a-f]+)\s+s3=([0-9a-f]+)", re.IGNORECASE)


def parse_words(data: bytes) -> tuple[list[int], bool]:
    words: list[int] = []
    for offset in range(0, len(data) - 1, 2):
        value = struct.unpack_from("<H", data, offset)[0]
        words.append(value)
        if value == 0x8000:
            return words, True
    return words, False


def find_breakpoint(response: dict[str, Any], address: int) -> dict[str, Any] | None:
    for item in response.get("breakpoints", []):
        if int(item.get("address", -1)) == address:
            return item
    return None


def runtime_layout(module_response: dict[str, Any]) -> tuple[int, int, int]:
    module = next(
        (item for item in module_response.get("modules", []) if item.get("name") == GAME_MODULE),
        None,
    )
    if module is None:
        raise RuntimeError(f"active game module {GAME_MODULE!r} was not found")
    # PPSSPP reports the PSP ELF relocation base, so ELF virtual addresses are
    # added directly.  The .text section's own sh_addr (0x40) is not subtracted.
    load_bias = int(module["address"])
    return load_bias, load_bias + HOOK_ELF_ADDRESS, load_bias + TARGET_ELF_ADDRESS


def expected_words(target_address: int) -> tuple[int, int]:
    jal = (3 << 26) | ((target_address >> 2) & 0x03FFFFFF)
    return MOVE_A0_S3, jal


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture the raw 16-bit stream entering the Spanish parser patch")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-bytes", type=lambda value: int(value, 0), default=0x1000)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "analysis/debugger/dialogue-stream.json",
    )
    args = parser.parse_args()

    session = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    armed = False
    hook_address: int | None = None
    report: dict[str, Any] = {}
    try:
        game = session.request("game.status")
        report["game_status"] = game
        modules = session.request("hle.module.list")
        load_bias, hook_address, target_address = runtime_layout(modules)
        expected = expected_words(target_address)
        report.update({
            "module_list": modules,
            "load_bias": f"0x{load_bias:08X}",
            "hook_elf_address": f"0x{HOOK_ELF_ADDRESS:08X}",
            "hook_address": f"0x{hook_address:08X}",
            "target_elf_address": f"0x{TARGET_ELF_ADDRESS:08X}",
            "target_address": f"0x{target_address:08X}",
            "expected_words": [f"0x{word:08X}" for word in expected],
        })
        signature = session.read(hook_address, 8)
        actual_words = struct.unpack("<II", signature)
        report["actual_words"] = [f"0x{word:08X}" for word in actual_words]
        if actual_words != expected:
            raise RuntimeError(
                "Spanish parser hook signature mismatch: "
                f"expected {expected!r}, got {actual_words!r}"
            )

        input("Leave the current textbox visible. Press ENTER to arm, then advance exactly ONE textbox: ")
        session.request(
            "cpu.breakpoint.add",
            address=hook_address,
            enabled=False,
            log=True,
            logFormat=LOG_FORMAT,
        )
        armed = True
        installed = find_breakpoint(session.request("cpu.breakpoint.list"), hook_address)
        report["installed_breakpoint"] = installed
        if installed is None or installed.get("enabled") or not installed.get("log"):
            raise RuntimeError(f"unexpected installed CPU breakpoint: {installed}")

        print("ARMED (log-only). Advance exactly one textbox in PPSSPP.")
        started = time.monotonic()
        event = session.wait_event(
            {"log"}, args.timeout,
            predicate=lambda item: "BOKU_STREAM" in str(item.get("message") or ""),
        )
        elapsed = time.monotonic() - started
        match = LOG_RE.search(str(event.get("message") or ""))
        if match is None:
            raise RuntimeError(f"could not parse stream log event: {event}")
        pc = int(match.group(1), 16)
        pointer = int(match.group(2), 16)
        raw = session.read(pointer, args.max_bytes)
        words, terminated = parse_words(raw)
        used = len(words) * 2
        report.update({
            "result": "hit",
            "elapsed_seconds": elapsed,
            "event": event,
            "pc": f"0x{pc:08X}",
            "stream_pointer": f"0x{pointer:08X}",
            "terminated": terminated,
            "stream_size": used,
            "stream_hex": raw[:used].hex().upper(),
            "stream_words": [f"0x{word:04X}" for word in words],
        })
        print(f"Captured {len(words)} words from 0x{pointer:08X}; terminated={terminated}")
    except Exception as exc:
        report.setdefault("result", "error")
        report["error"] = str(exc)
        raise
    finally:
        if armed and hook_address is not None:
            try:
                session.request("cpu.breakpoint.remove", address=hook_address)
            except Exception as exc:
                report["remove_warning"] = str(exc)
        session.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
