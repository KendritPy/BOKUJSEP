#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ppsspp_debug import PPSSPPDebugger

ROOT = Path(__file__).resolve().parents[1]


def integer(value: str) -> int:
    return int(value, 0)


def parse_hex(value: str) -> int:
    return int(value, 16) if value.lower().startswith("0x") else int(value, 0)


def function_ranges(response: dict[str, Any]) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    for item in response.get("functions", []):
        try:
            start = int(item.get("address", 0))
            size = int(item.get("size", 0))
        except (TypeError, ValueError):
            continue
        if size <= 0:
            continue
        out.append((start, start + size, str(item.get("name") or "")))
    out.sort()
    return out


def containing_function(ranges: list[tuple[int, int, str]], address: int) -> tuple[int, int, str] | None:
    # Function lists are only a few thousand entries; linear scan is fine for tens of candidates.
    for start, end, name in ranges:
        if start <= address < end:
            return start, end, name
        if start > address:
            break
    return None


def containing_module(modules: dict[str, Any], address: int) -> dict[str, Any] | None:
    for item in modules.get("modules", []):
        try:
            start = int(item.get("address", 0))
            size = int(item.get("size", 0))
        except (TypeError, ValueError):
            continue
        if start <= address < start + size:
            return item
    return None


def compact_disasm(response: dict[str, Any]) -> list[str]:
    lines = response.get("lines", [])
    return [str(line) for line in lines] if isinstance(lines, list) else []


def classify_one(
    debugger: PPSSPPDebugger,
    funcs: list[tuple[int, int, str]],
    modules: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    start = parse_hex(candidate["start"])
    end = parse_hex(candidate["end_inclusive"])
    func = containing_function(funcs, start)
    module = containing_module(modules, start)
    size = min(16, max(4, end - start + 1))
    try:
        raw = debugger.read(start, size).hex().upper()
    except Exception as exc:
        raw = f"ERROR: {exc}"
    try:
        disasm = compact_disasm(debugger.request(
            "memory.disasm", address=start & ~3, count=4, displaySymbols=True, compact=True
        ))
    except Exception as exc:
        disasm = [f"ERROR: {exc}"]

    # Membership in PPSSPP's analyzed function map is strong evidence of code.
    # Disassembly alone is not: arbitrary data can decode as legal MIPS instructions.
    classification = "CODE" if func else "DATA_OR_UNKNOWN"
    return {
        **candidate,
        "classification": classification,
        "function": None if func is None else {
            "start": f"0x{func[0]:08X}",
            "end_exclusive": f"0x{func[1]:08X}",
            "name": func[2],
        },
        "module": module,
        "current_hex": raw,
        "disasm": disasm,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify stable-diff candidates as code vs data before setting memchecks.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "analysis" / "debugger" / "dialogue-stable-diff.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "debugger" / "dialogue-candidates-classified.json",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"missing {args.input}; run probe-stable-diff.bat first")
    report = json.loads(args.input.read_text(encoding="utf-8"))
    runs = report.get("clean_runs", [])
    if not runs:
        raise SystemExit("stable-diff report contains no clean runs")

    debugger = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    try:
        game = debugger.request("game.status")
        funcs_raw = debugger.request("hle.func.list")
        modules = debugger.request("hle.module.list")
        funcs = function_ranges(funcs_raw)
        classified = [classify_one(debugger, funcs, modules, item) for item in runs]
    finally:
        debugger.close()

    data_candidates = [item for item in classified if item["classification"] != "CODE"]
    code_candidates = [item for item in classified if item["classification"] == "CODE"]
    data_candidates.sort(key=lambda item: (-int(item.get("changed", 0)), int(item.get("gaps", 0)), item["start"]))

    print(f"Known PPSSPP functions: {len(funcs):,}")
    print(f"Stable-diff runs classified: {len(classified)}")
    print(f"Rejected as executable code: {len(code_candidates)}")
    print(f"Remaining data/unknown runs: {len(data_candidates)}")

    if code_candidates:
        print("\nTop rejected CODE candidates:")
        for item in code_candidates[:10]:
            fn = item.get("function") or {}
            print(
                f"  {item['start']}-{item['end_inclusive']} changed={item.get('changed')} "
                f"function={fn.get('name') or fn.get('start')} hex={item.get('current_hex')}"
            )
            for line in item.get("disasm", [])[:2]:
                print(f"      {line}")

    print("\nBest remaining DATA/UNKNOWN candidates:")
    if not data_candidates:
        print("  none")
    else:
        for index, item in enumerate(data_candidates[:20], 1):
            module = item.get("module") or {}
            module_name = module.get("name") or "(no module)"
            print(
                f"[{index:02d}] {item['start']}-{item['end_inclusive']} "
                f"changed={item.get('changed')} span={item.get('span')} gaps={item.get('gaps')} "
                f"module={module_name}"
            )
            print(f"     current={item.get('current_hex')}")
            for line in item.get("disasm", [])[:2]:
                print(f"     {line}")

    output = {
        "game_status": game,
        "known_function_count": len(funcs),
        "summary": {
            "runs": len(classified),
            "code": len(code_candidates),
            "data_or_unknown": len(data_candidates),
        },
        "data_candidates": data_candidates,
        "code_candidates": code_candidates,
        "modules": modules,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
