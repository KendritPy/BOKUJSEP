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
DEFAULT_DELAYS = (0.17, 0.31, 0.47, 0.73, 1.11)


def cpu_status(debugger: PPSSPPDebugger) -> dict[str, Any]:
    return debugger.request("cpu.status")


def wait_stepping(debugger: PPSSPPDebugger, stepping: bool, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = cpu_status(debugger)
        if bool(last.get("stepping")) == stepping:
            return
        time.sleep(0.02)
    raise RuntimeError(f"CPU did not reach stepping={stepping}; last={last}")


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
    already = bool(status.get("stepping"))
    print(f"\n[{label}] capture")
    if not already:
        debugger.fire("cpu.stepping")
        wait_stepping(debugger, True)
    try:
        return read_ram(debugger)
    finally:
        try:
            if bool(cpu_status(debugger).get("stepping")):
                debugger.fire("cpu.resume")
                wait_stepping(debugger, False)
        except Exception as exc:
            print(f"WARNING: resume failed: {exc}")
            print("Run: .venv\\Scripts\\python.exe tools\\ppsspp_debug.py resume")


def accumulate_noise(mask: bytearray, baseline: bytes, sample: bytes) -> int:
    newly_changed = 0
    for i, (a, b) in enumerate(zip(baseline, sample)):
        if a != b and not mask[i]:
            mask[i] = 1
            newly_changed += 1
    return newly_changed


def capture_stability_group(
    debugger: PPSSPPDebugger,
    label: str,
    delays: tuple[float, ...],
) -> tuple[bytes, bytearray, list[dict[str, Any]], int]:
    baseline = snapshot(debugger, f"{label} baseline")
    noise = bytearray(RAM_SIZE)
    total_noisy = 0
    samples: list[dict[str, Any]] = []
    for index, delay in enumerate(delays, 1):
        print(f"Waiting {delay:.2f}s with the SAME textbox...")
        time.sleep(delay)
        current = snapshot(debugger, f"{label} stability {index}/{len(delays)}")
        newly_noisy = accumulate_noise(noise, baseline, current)
        total_noisy += newly_noisy
        samples.append({
            "delay_seconds": delay,
            "newly_noisy_bytes": newly_noisy,
            "total_noisy_bytes": total_noisy,
        })
        print(f"{label}: +{newly_noisy:,} newly noisy bytes; total={total_noisy:,}")
    return baseline, noise, samples, total_noisy


def changed_mask(left: bytes, right: bytes) -> bytearray:
    return bytearray(a != b for a, b in zip(left, right))


def is_ram_pointer(value: int) -> bool:
    return RAM_BASE <= value < RAM_BASE + RAM_SIZE


@dataclass
class Run:
    start: int
    end: int
    changed: int
    gaps: int

    @property
    def span(self) -> int:
        return self.end - self.start


def merged_runs(mask: bytearray, max_gap: int = 3, min_changed: int = 3) -> list[Run]:
    indices = [i for i, value in enumerate(mask) if value]
    if not indices:
        return []
    result: list[Run] = []
    start = indices[0]
    last = indices[0]
    changed = 1
    gaps = 0
    for idx in indices[1:]:
        gap = idx - last - 1
        if gap <= max_gap:
            changed += 1
            gaps += max(0, gap)
            last = idx
            continue
        if changed >= min_changed:
            result.append(Run(start, last + 1, changed, gaps))
        start = last = idx
        changed = 1
        gaps = 0
    if changed >= min_changed:
        result.append(Run(start, last + 1, changed, gaps))
    result.sort(key=lambda r: (-r.changed, r.gaps, r.start))
    return result


def page_report(transition: bytearray, noise_a: bytearray, noise_b: bytearray, clean: bytearray, limit: int) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for start in range(0, RAM_SIZE, PAGE_SIZE):
        end = min(start + PAGE_SIZE, RAM_SIZE)
        t = sum(transition[start:end])
        if not t:
            continue
        a = sum(noise_a[start:end])
        b = sum(noise_b[start:end])
        c = sum(clean[start:end])
        score = c * 8 - (a + b) * 2
        pages.append({
            "address": f"0x{RAM_BASE + start:08X}",
            "transition": int(t),
            "clean": int(c),
            "noise_a": int(a),
            "noise_b": int(b),
            "score": int(score),
        })
    pages.sort(key=lambda x: (-x["score"], -x["clean"], x["noise_a"] + x["noise_b"], x["address"]))
    return pages[:limit]


def word_is_noisy(mask: bytearray, offset: int) -> bool:
    return bool(mask[offset] or mask[offset + 1] or mask[offset + 2] or mask[offset + 3])


def pointer_changes(a: bytes, b: bytes, noise_a: bytearray, noise_b: bytearray, limit: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for offset in range(0, RAM_SIZE - 3, 4):
        if word_is_noisy(noise_a, offset) or word_is_noisy(noise_b, offset):
            continue
        old = int.from_bytes(a[offset:offset + 4], "little")
        new = int.from_bytes(b[offset:offset + 4], "little")
        if old == new:
            continue
        if not (is_ram_pointer(old) or is_ram_pointer(new)):
            continue
        out.append({
            "address": f"0x{RAM_BASE + offset:08X}",
            "old": f"0x{old:08X}",
            "new": f"0x{new:08X}",
            "old_ptr": is_ram_pointer(old),
            "new_ptr": is_ram_pointer(new),
        })
    out.sort(key=lambda x: (-(int(x["old_ptr"]) + int(x["new_ptr"])), x["address"]))
    return out[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-sample differential RAM probe for Boku dialogue state.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--page-limit", type=int, default=30)
    parser.add_argument("--pointer-limit", type=int, default=50)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "debugger" / "dialogue-stable-diff.json",
    )
    args = parser.parse_args()

    debugger = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    try:
        game = debugger.request("game.status")
        print(f"game.status: {game}")
        print("\nPHASE A: leave the CURRENT textbox fully visible and do not advance it.")
        a, noise_a, samples_a, total_noise_a = capture_stability_group(debugger, "A", DEFAULT_DELAYS)

        print("\nAdvance EXACTLY ONE dialogue box now.")
        print("Wait until the next textbox is fully visible, then return here.")
        input(">>> Press ENTER when the NEXT textbox is stable: ")

        b, noise_b, samples_b, total_noise_b = capture_stability_group(debugger, "B", DEFAULT_DELAYS)
    finally:
        debugger.close()

    transition = changed_mask(a, b)
    clean = bytearray(
        int(bool(transition[i]) and not bool(noise_a[i]) and not bool(noise_b[i]))
        for i in range(RAM_SIZE)
    )
    total_transition = int(sum(transition))
    total_clean = int(sum(clean))

    print("\n=== Robust differential summary ===")
    print(f"A bytes ever noisy across {len(DEFAULT_DELAYS)} samples: {total_noise_a:,}")
    print(f"B bytes ever noisy across {len(DEFAULT_DELAYS)} samples: {total_noise_b:,}")
    print(f"A -> B changed bytes: {total_transition:,}")
    print(f"surviving line-specific bytes: {total_clean:,}")

    pages = page_report(transition, noise_a, noise_b, clean, args.page_limit)
    print("\nTop candidate 256-byte pages:")
    for i, p in enumerate(pages[:15], 1):
        print(
            f"[{i:02d}] {p['address']} clean={p['clean']:3d} transition={p['transition']:3d} "
            f"noise={p['noise_a']:3d}+{p['noise_b']:3d} score={p['score']:4d}"
        )

    runs = merged_runs(clean, max_gap=3, min_changed=3)[:100]
    print("\nTop surviving runs:")
    if not runs:
        print("  none")
    else:
        for i, run in enumerate(runs[:20], 1):
            print(
                f"[{i:02d}] 0x{RAM_BASE + run.start:08X}-0x{RAM_BASE + run.end - 1:08X} "
                f"changed={run.changed} span={run.span} gaps={run.gaps}"
            )

    pointers = pointer_changes(a, b, noise_a, noise_b, args.pointer_limit)
    print("\nStable changed words that look like RAM pointers:")
    if not pointers:
        print("  none")
    else:
        for i, item in enumerate(pointers[:20], 1):
            print(f"[{i:02d}] {item['address']}: {item['old']} -> {item['new']}")

    report = {
        "game_status": game,
        "delays_seconds": list(DEFAULT_DELAYS),
        "samples_a": samples_a,
        "samples_b": samples_b,
        "summary": {
            "noise_a_ever_changed": total_noise_a,
            "noise_b_ever_changed": total_noise_b,
            "transition_changed": total_transition,
            "clean_line_specific": total_clean,
        },
        "candidate_pages": pages,
        "clean_runs": [
            {
                "start": f"0x{RAM_BASE + r.start:08X}",
                "end_inclusive": f"0x{RAM_BASE + r.end - 1:08X}",
                "changed": r.changed,
                "span": r.span,
                "gaps": r.gaps,
            }
            for r in runs
        ],
        "pointer_changes": pointers,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
