#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from ppsspp_debug import PPSSPPDebugger

ROOT = Path(__file__).resolve().parents[1]
PAGE_SIZE = 0x100
DELAYS = (0.17, 0.31, 0.47, 0.73, 1.11)

# Every page that contained at least one surviving clean byte in the corrected
# replacements=False full-RAM differential from 2026-09-01.
DEFAULT_PAGES = (
    0x08929C00,
    0x08929D00,
    0x08B74100,
    0x08934200,
    0x0892E000,
    0x0892C000,
    0x0892EB00,
)


def wait_stepping(debugger: PPSSPPDebugger, wanted: bool, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = debugger.request("cpu.status")
        if bool(last.get("stepping")) == wanted:
            return
        time.sleep(0.01)
    raise RuntimeError(f"CPU did not reach stepping={wanted}; last={last}")


def snapshot(debugger: PPSSPPDebugger, label: str, pages: tuple[int, ...]) -> dict[int, bytes]:
    status = debugger.request("cpu.status")
    already = bool(status.get("stepping"))
    print(f"[{label}]", end=" ")
    if not already:
        debugger.fire("cpu.stepping")
        wait_stepping(debugger, True)
    try:
        result = {address: debugger.read(address, PAGE_SIZE) for address in pages}
        for address, blob in result.items():
            if len(blob) != PAGE_SIZE:
                raise RuntimeError(
                    f"short read at 0x{address:08X}: expected {PAGE_SIZE}, got {len(blob)}"
                )
        print("captured")
        return result
    finally:
        if not already:
            try:
                debugger.fire("cpu.resume")
                wait_stepping(debugger, False)
            except Exception as exc:
                print(f"WARNING: resume failed: {exc}")


def build_noise(
    debugger: PPSSPPDebugger,
    label: str,
    pages: tuple[int, ...],
) -> tuple[dict[int, bytes], dict[int, bytearray], list[dict[str, Any]]]:
    baseline = snapshot(debugger, f"{label} baseline", pages)
    noise = {address: bytearray(PAGE_SIZE) for address in pages}
    samples: list[dict[str, Any]] = []
    for index, delay in enumerate(DELAYS, 1):
        time.sleep(delay)
        current = snapshot(debugger, f"{label} stability {index}/{len(DELAYS)}", pages)
        new_count = 0
        total_count = 0
        for address in pages:
            base = baseline[address]
            now = current[address]
            mask = noise[address]
            for offset, (old, new) in enumerate(zip(base, now)):
                if old != new and not mask[offset]:
                    mask[offset] = 1
                    new_count += 1
            total_count += sum(mask)
        samples.append({
            "delay_seconds": delay,
            "newly_noisy_bytes": new_count,
            "total_noisy_bytes": total_count,
        })
        print(f"    {label}: +{new_count} noisy; total={total_count}")
    return baseline, noise, samples


def function_for(address: int, functions: list[dict[str, Any]]) -> dict[str, Any] | None:
    for fn in functions:
        start = int(fn.get("address", 0))
        size = int(fn.get("size", 0))
        if start <= address < start + size:
            return {
                "name": fn.get("name"),
                "start": f"0x{start:08X}",
                "end_exclusive": f"0x{start + size:08X}",
            }
    return None


def module_for(address: int, modules: list[dict[str, Any]]) -> dict[str, Any] | None:
    for module in modules:
        start = int(module.get("address", 0))
        size = int(module.get("size", 0))
        if start <= address < start + size:
            return {
                "name": module.get("name"),
                "address": f"0x{start:08X}",
                "size": size,
                "isActive": module.get("isActive"),
            }
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fast exact-byte differential over only the pages that survived the corrected full-RAM probe."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "debugger" / "dialogue-targeted-diff.json",
    )
    args = parser.parse_args()

    pages = DEFAULT_PAGES
    debugger = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    try:
        game = debugger.request("game.status")
        print(f"game.status: {game}")
        print(f"Target pages: {', '.join(f'0x{x:08X}' for x in pages)}")
        print("\nPHASE A: leave the known current textbox fully visible and untouched.")
        a, noise_a, samples_a = build_noise(debugger, "A", pages)

        print("\nAdvance EXACTLY ONE textbox in PPSSPP and wait until the next one is fully visible.")
        input(">>> Press ENTER here when textbox B is stable: ")
        b, noise_b, samples_b = build_noise(debugger, "B", pages)

        try:
            function_response = debugger.request("hle.func.list")
            functions = list(function_response.get("functions", []))
        except Exception as exc:
            print(f"WARNING: hle.func.list failed: {exc}")
            functions = []
        try:
            module_response = debugger.request("hle.module.list")
            modules = list(module_response.get("modules", []))
        except Exception as exc:
            print(f"WARNING: hle.module.list failed: {exc}")
            modules = []
    finally:
        debugger.close()

    clean_bytes: list[dict[str, Any]] = []
    page_summary: list[dict[str, Any]] = []
    for page in pages:
        transition = 0
        clean = 0
        noisy_a_count = int(sum(noise_a[page]))
        noisy_b_count = int(sum(noise_b[page]))
        for offset, (old, new) in enumerate(zip(a[page], b[page])):
            if old == new:
                continue
            transition += 1
            if noise_a[page][offset] or noise_b[page][offset]:
                continue
            clean += 1
            address = page + offset
            fn = function_for(address, functions)
            module = module_for(address, modules)
            clean_bytes.append({
                "address": f"0x{address:08X}",
                "page": f"0x{page:08X}",
                "offset": offset,
                "a": f"0x{old:02X}",
                "b": f"0x{new:02X}",
                "function": fn,
                "module": module,
            })
        page_summary.append({
            "address": f"0x{page:08X}",
            "transition": transition,
            "clean": clean,
            "noise_a": noisy_a_count,
            "noise_b": noisy_b_count,
        })

    # Add aligned 16/32-bit context around every clean byte so we can recognize
    # counters, pointers, coordinates, flags, etc. without another probe.
    contexts: dict[str, dict[str, Any]] = {}
    for item in clean_bytes:
        address = int(item["address"], 16)
        page = int(item["page"], 16)
        offset = int(item["offset"])
        for width in (2, 4):
            aligned = address & ~(width - 1)
            aligned_offset = aligned - page
            if 0 <= aligned_offset <= PAGE_SIZE - width:
                key = f"0x{aligned:08X}/{width}"
                if key not in contexts:
                    contexts[key] = {
                        "address": f"0x{aligned:08X}",
                        "width": width,
                        "a_hex": a[page][aligned_offset:aligned_offset + width].hex().upper(),
                        "b_hex": b[page][aligned_offset:aligned_offset + width].hex().upper(),
                        "a_le": int.from_bytes(a[page][aligned_offset:aligned_offset + width], "little"),
                        "b_le": int.from_bytes(b[page][aligned_offset:aligned_offset + width], "little"),
                        "function": function_for(aligned, functions),
                        "module": module_for(aligned, modules),
                    }

    clean_bytes.sort(key=lambda x: x["address"])
    context_list = sorted(contexts.values(), key=lambda x: (x["address"], x["width"]))

    print("\n=== Exact targeted differential ===")
    print(f"Clean bytes surviving all same-line samples: {len(clean_bytes)}")
    if not clean_bytes:
        print("  none")
    for item in clean_bytes:
        kind = "CODE" if item["function"] else "DATA/UNKNOWN"
        print(f"  {item['address']}: {item['a']} -> {item['b']}  {kind}")

    print("\nAligned value context:")
    for item in context_list:
        if item["width"] == 2:
            print(
                f"  {item['address']} u16: {item['a_hex']} ({item['a_le']}) -> "
                f"{item['b_hex']} ({item['b_le']})"
            )
        else:
            print(
                f"  {item['address']} u32: {item['a_hex']} (0x{item['a_le']:08X}) -> "
                f"{item['b_hex']} (0x{item['b_le']:08X})"
            )

    report = {
        "game_status": game,
        "pages": [f"0x{x:08X}" for x in pages],
        "delays_seconds": list(DELAYS),
        "samples_a": samples_a,
        "samples_b": samples_b,
        "page_summary": page_summary,
        "clean_bytes": clean_bytes,
        "aligned_context": context_list,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
