#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from ppsspp_debug import PPSSPPDebugger

ROOT = Path(__file__).resolve().parents[1]
MEMCHECK_LOG_RE = re.compile(
    r"CHK\s+Write\d+\([^)]+\)\s+at\s+([0-9A-Fa-f]+).*?\bpc=([0-9A-Fa-f]+)",
    re.IGNORECASE,
)
TRACE_LOG_FORMAT = (
    "BOKU_WATCH pc={pc:x} ra={ra:x} sp={sp:x} "
    "a0={a0:x} a1={a1:x} a2={a2:x} a3={a3:x} "
    "v0={v0:x} v1={v1:x} t0={t0:x} t1={t1:x} "
    "t2={t2:x} t3={t3:x} t4={t4:x} t5={t5:x} "
    "s0={s0:x} s1={s1:x} s2={s2:x} s3={s3:x} fp={fp:x} gp={gp:x}"
)


def integer(value: str) -> int:
    return int(value, 0)


def compact_regs(response: dict[str, Any]) -> dict[str, str]:
    output: dict[str, str] = {}
    for category in response.get("categories", []):
        if category.get("name") != "GPR":
            continue
        for name, value in zip(category.get("registerNames", []), category.get("uintValues", [])):
            output[str(name)] = f"0x{int(value):08X}"
    return output


def breakpoint_matches(hit: Any, address: int, size: int) -> bool:
    if not isinstance(hit, dict) or hit.get("kind") != "memory":
        return False
    bp = hit.get("breakpoint") or {}
    start = bp.get("start")
    end = bp.get("end")
    if start is not None:
        try:
            if int(start) != address:
                return False
        except (TypeError, ValueError):
            return False
    actual = hit.get("address")
    if actual is not None:
        try:
            actual_int = int(actual)
        except (TypeError, ValueError):
            return False
        # A store may begin just before our range and overlap it, so accept either
        # an access address inside the range or an access interval overlapping it.
        hit_size = int(hit.get("size") or 1)
        if actual_int + hit_size <= address or actual_int >= address + size:
            return False
    if start is None and actual is None:
        return False
    if end is not None:
        try:
            end_int = int(end)
            if end_int not in (address + size, address + size - 1):
                if actual is None:
                    return False
        except (TypeError, ValueError):
            pass
    return True


def ensure_running(session: PPSSPPDebugger) -> None:
    status = session.request("cpu.status")
    if not status.get("stepping"):
        return
    print("CPU was already stepping; resuming before arming.")
    session.fire("cpu.resume")
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        status = session.request("cpu.status")
        if not status.get("stepping"):
            return
        time.sleep(0.02)
    raise RuntimeError("CPU would not resume before arming")


def stepping_matches_memcheck(event: dict[str, Any], address: int, size: int) -> bool:
    """Accept both PPSSPP 1.20.4 and newer enriched stepping events."""
    hit = event.get("hit")
    if breakpoint_matches(hit, address, size):
        return True
    if event.get("event") != "cpu.stepping":
        return False
    if event.get("reason") != "memory.breakpoint":
        return False
    try:
        return int(event.get("relatedAddress")) == address
    except (TypeError, ValueError):
        return False


def memcheck_log_writer(event: dict[str, Any], address: int, size: int) -> int | None:
    """Extract the writer PC from PPSSPP's exact memcheck log fallback."""
    if event.get("event") != "log":
        return None
    match = MEMCHECK_LOG_RE.search(str(event.get("message") or ""))
    if match is None:
        return None
    actual = int(match.group(1), 16)
    if not (address <= actual < address + size):
        return None
    return int(match.group(2), 16)


def wait_for_our_hit(
    session: PPSSPPDebugger, address: int, size: int, timeout: float
) -> tuple[dict[str, Any], int | None]:
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("no matching memory-breakpoint event before timeout")
        event = session.wait_event({"cpu.stepping", "log"}, remaining)
        if stepping_matches_memcheck(event, address, size):
            return event, None

        logged_pc = memcheck_log_writer(event, address, size)
        if logged_pc is not None:
            # Some 1.20.4 interpreter runs emit the exact memcheck log and then
            # immediately resume without delivering a usable stepping event.
            # Preserve that real writer evidence instead of misreporting a timeout.
            return event, logged_pc

        if event.get("event") == "log":
            continue

        print(
            "Ignoring unrelated cpu.stepping event "
            f"(reason={event.get('reason')!r}, hit={event.get('hit')!r}); resuming."
        )
        session.fire("cpu.resume")
        time.sleep(0.03)


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def find_armed_memcheck(response: dict[str, Any], address: int, size: int) -> dict[str, Any] | None:
    for item in response.get("breakpoints", []):
        try:
            if int(item.get("address")) == address and int(item.get("size")) == size:
                return item
        except (TypeError, ValueError):
            continue
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture a real PPSSPP memory-breakpoint broadcast for a dialogue candidate.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--address", type=integer, default=0x0881C62C)
    parser.add_argument("--size", type=integer, default=4)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--log-only",
        action="store_true",
        help="log writes with pre-access registers instead of relying on PPSSPP's unstable pause",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "debugger" / "dialogue-watch-line.json",
    )
    args = parser.parse_args()

    session = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    armed = False
    game: dict[str, Any] | None = None
    baseline = b""
    modules: dict[str, Any] | None = None
    watched_disasm: dict[str, Any] | None = None
    armed_at: float | None = None
    armed_memcheck: dict[str, Any] | None = None
    broadcast_config: dict[str, Any] | None = None
    try:
        broadcast_config = session.request("broadcast.config.get")
        print(f"broadcast.config: {broadcast_config}")
        game = session.request("game.status")
        print(f"game.status: {game}")
        ensure_running(session)
        baseline = session.read(args.address, args.size)
        print(f"Candidate: 0x{args.address:08X}-0x{args.address + args.size - 1:08X}")
        print(f"Baseline: {baseline.hex().upper()}")

        try:
            modules = session.request("hle.module.list")
        except Exception as exc:
            modules = {"error": str(exc)}
        try:
            watched_disasm = session.request(
                "memory.disasm", address=args.address, count=6, displaySymbols=True, compact=True
            )
        except Exception as exc:
            watched_disasm = {"error": str(exc)}

        print("\nLeave the current textbox fully visible.")
        input("Press ENTER here to arm the real memcheck. Then switch to PPSSPP and advance exactly ONE textbox: ")

        # PPSSPP's WRITE_ONCHANGE is a modifier of WRITE, not a standalone
        # access mode. A valid write-change watch therefore requires BOTH bits:
        # write=True and change=True.
        memcheck_parameters: dict[str, Any] = {
            "address": args.address,
            "size": args.size,
            "enabled": not args.log_only,
            "log": True,
            "read": False,
            "write": True,
            "change": True,
        }
        if args.log_only:
            memcheck_parameters["logFormat"] = TRACE_LOG_FORMAT
        session.request("memory.breakpoint.add", **memcheck_parameters)
        armed = True

        listed = session.request("memory.breakpoint.list")
        armed_memcheck = find_armed_memcheck(listed, args.address, args.size)
        if armed_memcheck is None:
            raise RuntimeError("PPSSPP did not list the memory breakpoint after arming")
        print("Installed memcheck:")
        print(json.dumps(armed_memcheck, ensure_ascii=False, indent=2))
        if not armed_memcheck.get("write") or not armed_memcheck.get("change"):
            raise RuntimeError(f"PPSSPP installed unexpected memcheck flags: {armed_memcheck}")
        if args.log_only and armed_memcheck.get("enabled"):
            raise RuntimeError(f"PPSSPP installed a pausing log-only memcheck: {armed_memcheck}")

        armed_at = time.monotonic()
        print("ARMED AND VERIFIED. Now advance exactly one textbox in PPSSPP.")
        matched_event, logged_writer_pc = wait_for_our_hit(
            session, args.address, args.size, args.timeout
        )
        elapsed = time.monotonic() - armed_at

        if logged_writer_pc is not None and not args.log_only:
            # Best-effort pause for follow-up inspection.  This is later than
            # the store, so registers/backtrace must not be called pre-store.
            session.fire("cpu.stepping")
            try:
                session.wait_event({"cpu.stepping"}, 2.0)
            except TimeoutError:
                pass

        hit = matched_event.get("hit") or {
            "kind": "memory",
            "pc": matched_event.get("pc"),
            "address": matched_event.get("relatedAddress"),
            "size": None,
            "access": "write (inferred from installed memcheck)",
            "source": "PPSSPP 1.20.4 cpu.stepping broadcast",
            "breakpoint": {
                "start": args.address,
                "end": args.address + args.size,
            },
        }
        print(f"\nREAL MEMORY BREAKPOINT EVENT after {elapsed:.3f}s")
        print(json.dumps(hit, ensure_ascii=False, indent=2))

        deadline = time.monotonic() + 2.0
        cpu_status: dict[str, Any] = {}
        while time.monotonic() < deadline:
            cpu_status = session.request("cpu.status")
            if cpu_status.get("stepping"):
                break
            time.sleep(0.01)

        regs_raw: dict[str, Any] | None = None
        regs: dict[str, str] = {}
        if not args.log_only:
            try:
                regs_raw = session.request("cpu.getAllRegs")
                regs = compact_regs(regs_raw)
            except Exception as exc:
                print(f"WARNING: register capture failed: {exc}")

        backtrace: dict[str, Any] | None = None
        if not args.log_only:
            try:
                backtrace = session.request("hle.backtrace")
            except Exception as exc:
                print(f"WARNING: backtrace failed: {exc}")

        pc = int(
            logged_writer_pc
            or hit.get("pc")
            or matched_event.get("pc")
            or cpu_status.get("pc")
            or 0
        )
        try:
            pc_disasm = session.request(
                "memory.disasm", address=max(0x08000000, pc - 0x20), count=20,
                displaySymbols=True, compact=True,
            )
        except Exception as exc:
            pc_disasm = {"error": str(exc)}

        after = session.read(args.address, args.size)
        listed_after = session.request("memory.breakpoint.list")
        memcheck_after = find_armed_memcheck(listed_after, args.address, args.size)
        write_report(args.output, {
            "result": "logged_hit" if logged_writer_pc is not None else "hit",
            "game_status": game,
            "broadcast_config": broadcast_config,
            "watch": {
                "address": f"0x{args.address:08X}",
                "size": args.size,
                "baseline_hex": baseline.hex().upper(),
                "after_hex": after.hex().upper(),
                "elapsed_seconds": elapsed,
            },
            "installed_memcheck": armed_memcheck,
            "memcheck_at_hit": memcheck_after,
            "breakpoint_event": matched_event,
            "writer_pc": f"0x{pc:08X}" if pc else None,
            "probe_mode": "log-only" if args.log_only else "pause",
            "capture_timing": (
                "non-pausing logFormat; authoritative pre-access registers are in breakpoint_event.message"
                if logged_writer_pc is not None
                else "memory-breakpoint stop; registers are pre-store"
            ),
            "cpu_status": cpu_status,
            "registers": regs,
            "registers_raw": regs_raw,
            "backtrace": backtrace,
            "watched_address_disasm": watched_disasm,
            "pc_disasm": pc_disasm,
            "modules": modules,
        })

    except TimeoutError as exc:
        print(f"\n{exc}")
        print("If you advanced the textbox, this watched value was not changed by a matching CPU write during the window.")
        try:
            after = session.read(args.address, args.size)
            after_hex = after.hex().upper()
        except Exception as read_exc:
            after_hex = None
            session.pending.append({"event": "probe.read_after_timeout.error", "message": str(read_exc)})
        elapsed = time.monotonic() - armed_at if armed_at is not None else None
        memcheck_after: dict[str, Any] | None = None
        try:
            listed_after = session.request("memory.breakpoint.list")
            memcheck_after = find_armed_memcheck(listed_after, args.address, args.size)
        except Exception as list_exc:
            session.pending.append({
                "event": "probe.memcheck_list_after_timeout.error",
                "message": str(list_exc),
            })
        write_report(args.output, {
            "result": "timeout",
            "error": str(exc),
            "game_status": game,
            "broadcast_config": broadcast_config,
            "watch": {
                "address": f"0x{args.address:08X}",
                "size": args.size,
                "baseline_hex": baseline.hex().upper(),
                "after_hex": after_hex,
                "elapsed_seconds": elapsed,
            },
            "installed_memcheck": armed_memcheck,
            "memcheck_after_timeout": memcheck_after,
            "pending_events": session.pending[-50:],
            "watched_address_disasm": watched_disasm,
            "modules": modules,
        })
    finally:
        if armed:
            try:
                session.request("memory.breakpoint.remove", address=args.address, size=args.size)
            except Exception as exc:
                print(f"WARNING: failed to remove memcheck: {exc}")
        try:
            status = session.request("cpu.status")
            if status.get("stepping"):
                session.fire("cpu.resume")
                print("CPU resumed.")
        except Exception as exc:
            print(f"WARNING: final resume check failed: {exc}")
        session.close()


if __name__ == "__main__":
    main()
