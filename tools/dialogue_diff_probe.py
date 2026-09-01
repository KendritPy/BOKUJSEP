#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ppsspp_debug import PPSSPPDebugger

ROOT = Path(__file__).resolve().parents[1]
RAM_BASE = 0x08000000
RAM_SIZE = 0x02000000
CHUNK_SIZE = 0x00100000
PAGE_SIZE = 0x100


def cpu_status(debugger: PPSSPPDebugger) -> dict[str, Any]:
    return debugger.request("cpu.status")


def wait_stepping(debugger: PPSSPPDebugger, stepping: bool, timeout: float = 5.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = cpu_status(debugger)
        if bool(last.get("stepping")) == stepping:
            return last
        time.sleep(0.03)
    raise RuntimeError(
        f"PPSSPP CPU did not reach stepping={stepping} within {timeout:.1f}s; last={last}"
    )


def read_ram(debugger: PPSSPPDebugger) -> bytes:
    data = bytearray()
    for offset in range(0, RAM_SIZE, CHUNK_SIZE):
        size = min(CHUNK_SIZE, RAM_SIZE - offset)
        data.extend(debugger.read(RAM_BASE + offset, size))
        print(f"read RAM 0x{offset + size:08X}/0x{RAM_SIZE:08X}", end="\r")
    print()
    return bytes(data)


def snapshot(debugger: PPSSPPDebugger, label: str) -> bytes:
    status = cpu_status(debugger)
    already_stepping = bool(status.get("stepping"))
    print(f"\n[{label}] cpu.status before capture: {status}")

    if not already_stepping:
        debugger.fire("cpu.stepping")
        wait_stepping(debugger, True)
        print(f"[{label}] CPU paused.")
    else:
        print(f"[{label}] CPU was already paused.")

    try:
        data = read_ram(debugger)
    finally:
        # This probe is interactive and always wants to hand control back to the user.
        # Resume even if the CPU happened to be stepping when we connected, which also
        # recovers from a previous failed probe that left PPSSPP suspended.
        try:
            if bool(cpu_status(debugger).get("stepping")):
                debugger.fire("cpu.resume")
                wait_stepping(debugger, False)
                print(f"[{label}] CPU resumed.")
        except Exception as exc:  # best-effort emergency recovery path
            print(f"[{label}] WARNING: automatic resume failed: {exc}")
            print("Run: .venv\\Scripts\\python.exe tools\\ppsspp_debug.py resume")
    return data


def changed_mask(left: bytes, right: bytes) -> bytearray:
    return bytearray(a != b for a, b in zip(left, right))


def count_mask(mask: bytearray, start: int, end: int) -> int:
    return sum(mask[start:end])


def is_ram_pointer(value: int) -> bool:
    return RAM_BASE <= value < RAM_BASE + RAM_SIZE


@dataclass
class CleanRun:
    start: int
    end: int
    changed: int
    gaps: int

    @property
    def length(self) -> int:
        return self.end - self.start


def clean_runs(clean: bytearray, max_gap: int = 2, min_changed: int = 4) -> list[CleanRun]:
    runs: list[CleanRun] = []
    i = 0
    n = len(clean)
    while i < n:
        while i < n and not clean[i]:
            i += 1
        if i >= n:
            break
        start = i
        last_change = i
        changed = 0
        gaps = 0
        while i < n:
            if clean[i]:
                changed += 1
                last_change = i
                i += 1
                continue
            gap_start = i
            while i < n and not clean[i] and i - gap_start <= max_gap:
                i += 1
            gap = i - gap_start
            if gap <= max_gap and i < n and clean[i]:
                gaps += gap
                continue
            i = gap_start
            break
        end = last_change + 1
        if changed >= min_changed:
            runs.append(CleanRun(start, end, changed, gaps))
        if i <= last_change:
            i = last_change + 1
    runs.sort(key=lambda run: (-run.changed, run.gaps, run.start))
    return runs


def page_report(
    transition: bytearray,
    noise_a: bytearray,
    noise_b: bytearray,
    clean: bytearray,
    limit: int,
) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for start in range(0, RAM_SIZE, PAGE_SIZE):
        end = min(start + PAGE_SIZE, RAM_SIZE)
        t = count_mask(transition, start, end)
        if not t:
            continue
        a = count_mask(noise_a, start, end)
        b = count_mask(noise_b, start, end)
        c = count_mask(clean, start, end)
        # Clean changes are line-transition changes that did not move during either
        # same-dialogue noise sample. Favor compact pages with many clean bytes and
        # penalize animation-heavy pages.
        score = c * 4 - (a + b)
        pages.append({
            "address": f"0x{RAM_BASE + start:08X}",
            "transition_changed_bytes": t,
            "clean_changed_bytes": c,
            "noise_a_bytes": a,
            "noise_b_bytes": b,
            "score": score,
        })
    pages.sort(
        key=lambda item: (
            -int(item["score"]),
            -int(item["clean_changed_bytes"]),
            int(item["noise_a_bytes"]) + int(item["noise_b_bytes"]),
            item["address"],
        )
    )
    return pages[:limit]


def pointer_changes(a: bytes, b: bytes, noise_a: bytearray, noise_b: bytearray, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for offset in range(0, RAM_SIZE - 3, 4):
        old = int.from_bytes(a[offset:offset + 4], "little")
        new = int.from_bytes(b[offset:offset + 4], "little")
        if old == new:
            continue
        # Reject words whose bytes were already moving during either same-line sample.
        if any(noise_a[offset:offset + 4]) or any(noise_b[offset:offset + 4]):
            continue
        old_ptr = is_ram_pointer(old)
        new_ptr = is_ram_pointer(new)
        if not (old_ptr or new_ptr):
            continue
        candidates.append({
            "address": f"0x{RAM_BASE + offset:08X}",
            "old": f"0x{old:08X}",
            "new": f"0x{new:08X}",
            "old_is_ram_pointer": old_ptr,
            "new_is_ram_pointer": new_ptr,
        })
    # Pointer->pointer transitions are the most interesting current-object/current-text candidates.
    candidates.sort(
        key=lambda item: (
            -(int(item["old_is_ram_pointer"]) + int(item["new_is_ram_pointer"])),
            item["address"],
        )
    )
    return candidates[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Differential PPSSPP RAM probe for locating Boku's current dialogue state."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--noise-delay", type=float, default=1.25)
    parser.add_argument("--page-limit", type=int, default=30)
    parser.add_argument("--pointer-limit", type=int, default=50)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "debugger" / "dialogue-diff.json",
    )
    parser.add_argument(
        "--save-snapshots",
        action="store_true",
        help="also save the four 32 MiB RAM snapshots under analysis/debugger",
    )
    args = parser.parse_args()

    debugger = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    try:
        game = debugger.request("game.status")
        print(f"game.status: {game}")
        print("\nPHASE A: keep the CURRENT dialogue box on screen. Do not advance it.")
        a0 = snapshot(debugger, "A0 current line")
        print(f"Waiting {args.noise_delay:.2f}s with the SAME dialogue to measure animation/background noise...")
        time.sleep(args.noise_delay)
        a1 = snapshot(debugger, "A1 same line noise sample")

        print("\nNow advance EXACTLY ONE dialogue box in PPSSPP.")
        print("Wait until the next line is fully visible and stable, then return here and press ENTER.")
        input(">>> Press ENTER only when the NEXT dialogue box is visible: ")
        b0 = snapshot(debugger, "B0 next line")
        print(f"Waiting {args.noise_delay:.2f}s with this SAME second line...")
        time.sleep(args.noise_delay)
        b1 = snapshot(debugger, "B1 same line noise sample")
    finally:
        debugger.close()

    noise_a = changed_mask(a0, a1)
    noise_b = changed_mask(b0, b1)
    transition = changed_mask(a1, b0)
    clean = bytearray(
        int(bool(transition[i]) and not bool(noise_a[i]) and not bool(noise_b[i]))
        for i in range(RAM_SIZE)
    )

    total_transition = sum(transition)
    total_noise_a = sum(noise_a)
    total_noise_b = sum(noise_b)
    total_clean = sum(clean)

    print("\n=== Differential summary ===")
    print(f"same-line noise A:       {total_noise_a:,} changed bytes")
    print(f"same-line noise B:       {total_noise_b:,} changed bytes")
    print(f"line transition A -> B:  {total_transition:,} changed bytes")
    print(f"clean line-specific set: {total_clean:,} changed bytes")

    pages = page_report(transition, noise_a, noise_b, clean, args.page_limit)
    print("\nTop 256-byte candidate pages:")
    for index, page in enumerate(pages[:15], 1):
        print(
            f"[{index:02d}] {page['address']} clean={page['clean_changed_bytes']:3d} "
            f"transition={page['transition_changed_bytes']:3d} "
            f"noise={page['noise_a_bytes']:3d}+{page['noise_b_bytes']:3d} "
            f"score={page['score']:4d}"
        )

    runs = clean_runs(clean, max_gap=2, min_changed=4)[:100]
    print("\nTop stable changed runs (small gaps merged):")
    for index, run in enumerate(runs[:20], 1):
        print(
            f"[{index:02d}] 0x{RAM_BASE + run.start:08X}-0x{RAM_BASE + run.end - 1:08X} "
            f"changed={run.changed} span={run.length} gaps={run.gaps}"
        )

    pointers = pointer_changes(a1, b0, noise_a, noise_b, args.pointer_limit)
    print("\nStable changed words that look like PSP RAM pointers:")
    if not pointers:
        print("  none")
    else:
        for index, item in enumerate(pointers[:20], 1):
            print(f"[{index:02d}] {item['address']}: {item['old']} -> {item['new']}")

    report = {
        "game_status": game,
        "noise_delay_seconds": args.noise_delay,
        "summary": {
            "noise_a_changed_bytes": total_noise_a,
            "noise_b_changed_bytes": total_noise_b,
            "transition_changed_bytes": total_transition,
            "clean_line_specific_changed_bytes": total_clean,
        },
        "candidate_pages": pages,
        "clean_runs": [
            {
                "start": f"0x{RAM_BASE + run.start:08X}",
                "end_inclusive": f"0x{RAM_BASE + run.end - 1:08X}",
                "changed_bytes": run.changed,
                "span_bytes": run.length,
                "merged_gap_bytes": run.gaps,
            }
            for run in runs
        ],
        "pointer_changes": pointers,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {args.output}")

    if args.save_snapshots:
        out = args.output.parent
        for name, data in (("diff-a0.bin", a0), ("diff-a1.bin", a1), ("diff-b0.bin", b0), ("diff-b1.bin", b1)):
            (out / name).write_bytes(data)
        print(f"Saved four RAM snapshots under {out}")


if __name__ == "__main__":
    main()
