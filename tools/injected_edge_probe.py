#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
import time
from pathlib import Path
from typing import Any

from dialogue_stream_probe import GAME_MODULE, runtime_layout
from ppsspp_debug import PPSSPPDebugger

ROOT = Path(__file__).resolve().parents[1]
EDGES = (
    (0x0003F074, "jal", 0x00115BF0),
    (0x000455F8, "j",   0x0011627C),
    (0x000482F4, "j",   0x00115A34),
    (0x000487F4, "j",   0x00115968),
    (0x00048860, "j",   0x001159DC),
    (0x0004B6CC, "j",   0x0011630C),
    (0x00079BFC, "j",   0x00115D2C),
)
LOG_RE = re.compile(r"BOKU_EDGE_(\d+)\s+pc=([0-9a-f]+)", re.IGNORECASE)


def branch_word(kind: str, target: int) -> int:
    opcode = 3 if kind == "jal" else 2
    return (opcode << 26) | ((target >> 2) & 0x03FFFFFF)


def find_breakpoint(response: dict[str, Any], address: int) -> dict[str, Any] | None:
    return next(
        (item for item in response.get("breakpoints", []) if int(item.get("address", -1)) == address),
        None,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Log which Spanish injected-region edges execute")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "analysis/debugger/injected-edges.json",
    )
    args = parser.parse_args()

    session = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    installed_addresses: list[int] = []
    report: dict[str, Any] = {"game_module": GAME_MODULE, "edges": [], "hits": []}
    try:
        report["game_status"] = session.request("game.status")
        modules = session.request("hle.module.list")
        load_bias, _, _ = runtime_layout(modules)
        report["module_list"] = modules
        report["load_bias"] = f"0x{load_bias:08X}"

        for index, (source_elf, kind, target_elf) in enumerate(EDGES):
            source = load_bias + source_elf
            target = load_bias + target_elf
            expected = branch_word(kind, target)
            actual = struct.unpack("<I", session.read(source, 4))[0]
            edge = {
                "index": index,
                "kind": kind,
                "source_elf": f"0x{source_elf:08X}",
                "source": f"0x{source:08X}",
                "target_elf": f"0x{target_elf:08X}",
                "target": f"0x{target:08X}",
                "expected_word": f"0x{expected:08X}",
                "actual_word": f"0x{actual:08X}",
            }
            report["edges"].append(edge)
            if actual != expected:
                raise RuntimeError(f"edge {index} signature mismatch: {edge}")

        input("Leave the current textbox visible. Press ENTER to arm, then advance exactly ONE textbox: ")
        for edge in report["edges"]:
            index = edge["index"]
            address = int(edge["source"], 16)
            log_format = (
                f"BOKU_EDGE_{index} pc={{pc:x}} a0={{a0:x}} a1={{a1:x}} "
                "a2={a2:x} a3={a3:x} v0={v0:x} v1={v1:x} "
                "s0={s0:x} s1={s1:x} s2={s2:x} s3={s3:x} "
                "s4={s4:x} s5={s5:x} s6={s6:x} s7={s7:x} sp={sp:x} ra={ra:x}"
            )
            session.request(
                "cpu.breakpoint.add", address=address, enabled=False, log=True,
                logFormat=log_format,
            )
            installed_addresses.append(address)
            installed = find_breakpoint(session.request("cpu.breakpoint.list"), address)
            if installed is None or installed.get("enabled") or not installed.get("log"):
                raise RuntimeError(f"unexpected installed CPU breakpoint: {installed}")

        print("ARMED (7 log-only edges). Advance exactly one textbox in PPSSPP.")
        started = time.monotonic()
        first = session.wait_event(
            {"log"}, args.timeout,
            predicate=lambda item: "BOKU_EDGE_" in str(item.get("message") or ""),
        )
        events = [first]
        # Preserve any additional patch edges reached by the same transition.
        grace_deadline = time.monotonic() + 1.0
        while True:
            remaining = grace_deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                events.append(session.wait_event(
                    {"log"}, remaining,
                    predicate=lambda item: "BOKU_EDGE_" in str(item.get("message") or ""),
                ))
            except TimeoutError:
                break

        for event in events:
            message = str(event.get("message") or "")
            match = LOG_RE.search(message)
            report["hits"].append({
                "edge_index": None if match is None else int(match.group(1)),
                "pc": None if match is None else f"0x{int(match.group(2), 16):08X}",
                "event": event,
            })
        report["elapsed_seconds"] = time.monotonic() - started
        report["result"] = "hit"
        print(f"Captured {len(events)} injected-edge event(s).")
    except Exception as exc:
        report.setdefault("result", "error")
        report["error"] = str(exc)
        raise
    finally:
        for address in installed_addresses:
            try:
                session.request("cpu.breakpoint.remove", address=address)
            except Exception as exc:
                report.setdefault("remove_warnings", []).append(str(exc))
        session.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
