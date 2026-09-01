#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import json
import time
from pathlib import Path
from typing import Any

from ppsspp_debug import PPSSPPDebugger

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADDRESS = 0x0892EC00
DEFAULT_SIZE = 0x34
F8_VK = 0x77


def integer(value: str) -> int:
    return int(value, 0)


def wait_cpu(debugger: PPSSPPDebugger, stepping: bool, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = debugger.request("cpu.status")
        if bool(last.get("stepping")) == stepping:
            return last
        time.sleep(0.015)
    raise TimeoutError(f"CPU did not reach stepping={stepping}; last={last}")


def resume_if_needed(debugger: PPSSPPDebugger) -> None:
    status = debugger.request("cpu.status")
    if bool(status.get("stepping")):
        debugger.fire("cpu.resume")
        wait_cpu(debugger, False, 5.0)


def wait_global_f8() -> None:
    if not hasattr(ctypes, "windll"):
        input("Press ENTER to arm the watchpoint, then immediately return to PPSSPP: ")
        return
    get_key = ctypes.windll.user32.GetAsyncKeyState
    print("Keep PPSSPP focused. Press F8 when the current textbox is stable to ARM the watchpoint.")
    print("Then advance exactly ONE dialogue box normally. You do not need to return to this window.")
    # Clear any prior press edge.
    while bool(get_key(F8_VK) & 0x8000):
        time.sleep(0.02)
    while True:
        if bool(get_key(F8_VK) & 0x8000):
            while bool(get_key(F8_VK) & 0x8000):
                time.sleep(0.01)
            return
        time.sleep(0.01)


def compact_regs(response: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for category in response.get("categories", []):
        if category.get("name") != "GPR":
            continue
        names = category.get("registerNames", [])
        values = category.get("uintValues", [])
        for name, value in zip(names, values):
            out[str(name)] = f"0x{int(value):08X}"
    return out


def changed_bytes(before: bytes, after: bytes, address: int) -> list[dict[str, Any]]:
    result = []
    for offset, (old, new) in enumerate(zip(before, after)):
        if old != new:
            result.append({
                "address": f"0x{address + offset:08X}",
                "offset": offset,
                "old": f"0x{old:02X}",
                "new": f"0x{new:02X}",
            })
    return result


def remove_watch(debugger: PPSSPPDebugger, address: int, size: int) -> None:
    try:
        debugger.request("memory.breakpoint.remove", address=address, size=size)
    except Exception as exc:
        print(f"WARNING: could not remove memory breakpoint cleanly: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch the dialogue-state candidate region and capture the MIPS writer when it changes."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--address", type=integer, default=DEFAULT_ADDRESS)
    parser.add_argument("--size", type=integer, default=DEFAULT_SIZE)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "debugger" / "dialogue-watch.json",
    )
    args = parser.parse_args()

    debugger = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    armed = False
    hit = False
    try:
        game = debugger.request("game.status")
        print(f"game.status: {game}")
        resume_if_needed(debugger)

        print(
            f"Candidate region: 0x{args.address:08X}-0x{args.address + args.size - 1:08X} "
            f"({args.size} bytes)"
        )
        baseline = debugger.read(args.address, args.size)
        print(f"Baseline: {baseline.hex().upper()}")

        wait_global_f8()

        # change=true means only writes that may actually modify memory should trip.
        debugger.request(
            "memory.breakpoint.add",
            address=args.address,
            size=args.size,
            enabled=True,
            log=False,
            read=False,
            write=False,
            change=True,
        )
        armed = True
        armed_at = time.monotonic()
        print("WATCHPOINT ARMED. Advance exactly ONE dialogue box now.")

        status = wait_cpu(debugger, True, args.timeout)
        hit = True
        elapsed = time.monotonic() - armed_at
        pc = int(status.get("pc", 0))
        print(f"\nWATCHPOINT HIT after {elapsed:.3f}s")
        print(f"PC = 0x{pc:08X}")

        after = debugger.read(args.address, args.size)
        changes = changed_bytes(baseline, after, args.address)
        print(f"Candidate bytes changed since arming: {len(changes)}")
        for item in changes[:40]:
            print(f"  {item['address']}: {item['old']} -> {item['new']}")

        regs_raw: dict[str, Any] | None = None
        regs: dict[str, str] = {}
        try:
            regs_raw = debugger.request("cpu.getAllRegs")
            regs = compact_regs(regs_raw)
            interesting = ["pc", "ra", "sp", "a0", "a1", "a2", "a3", "v0", "v1", "s0", "s1", "s2"]
            print("Registers:")
            for name in interesting:
                if name in regs:
                    print(f"  {name:>2} = {regs[name]}")
        except Exception as exc:
            print(f"WARNING: cpu.getAllRegs failed: {exc}")

        backtrace: dict[str, Any] | None = None
        try:
            backtrace = debugger.request("hle.backtrace")
            print("hle.backtrace captured.")
        except Exception as exc:
            print(f"NOTE: hle.backtrace unavailable/failed: {exc}")

        context_start = max(0x08000000, pc - 0x20)
        try:
            code_context = debugger.read(context_start, 0x60).hex().upper()
        except Exception:
            code_context = ""

        report = {
            "game_status": game,
            "watch": {
                "address": f"0x{args.address:08X}",
                "size": args.size,
                "end_inclusive": f"0x{args.address + args.size - 1:08X}",
                "elapsed_seconds_to_hit": elapsed,
            },
            "hit": {
                "cpu_status": status,
                "pc": f"0x{pc:08X}",
                "baseline_hex": baseline.hex().upper(),
                "after_hex": after.hex().upper(),
                "changed_bytes": changes,
                "registers": regs,
                "registers_raw": regs_raw,
                "backtrace": backtrace,
                "code_context_start": f"0x{context_start:08X}",
                "code_context_hex": code_context,
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")

    except TimeoutError as exc:
        print(f"\nNo write/change hit before timeout: {exc}")
        print("If you did advance the dialogue, this candidate region is not directly written during that transition.")
    finally:
        if armed:
            remove_watch(debugger, args.address, args.size)
        try:
            if bool(debugger.request("cpu.status").get("stepping")):
                debugger.fire("cpu.resume")
                wait_cpu(debugger, False, 5.0)
                print("CPU resumed.")
        except Exception as exc:
            print(f"WARNING: final CPU recovery failed: {exc}")
        debugger.close()

    if hit:
        print("\nImportant: tell me whether the watchpoint hit BEFORE or AFTER you actually advanced the textbox.")
        print("If it hit before you advanced, we caught background noise and will narrow to a cleaner byte.")


if __name__ == "__main__":
    main()
