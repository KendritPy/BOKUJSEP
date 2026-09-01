#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path
from typing import Any

from websocket import WebSocketTimeoutException, create_connection

ROOT = Path(__file__).resolve().parents[1]


def integer(value: str) -> int:
    return int(value, 0)


class Session:
    def __init__(self, host: str, port: int, timeout: float = 10.0):
        self.ws = create_connection(
            f"ws://{host}:{port}/debugger",
            subprotocols=["debugger.ppsspp.org"],
            timeout=timeout,
            suppress_origin=True,
        )
        self.ticket = 0
        self.pending: list[dict[str, Any]] = []
        self.request("version", name="BokuLangBreakpointProbe", version="0.3")

    def close(self) -> None:
        self.ws.close()

    def fire(self, event: str, **params: Any) -> None:
        self.ws.send(json.dumps({"event": event, **params}))

    def request(self, event: str, timeout: float | None = None, **params: Any) -> dict[str, Any]:
        self.ticket += 1
        ticket = self.ticket
        self.ws.send(json.dumps({"event": event, "ticket": ticket, **params}))
        previous_timeout = self.ws.gettimeout()
        if timeout is not None:
            self.ws.settimeout(timeout)
        try:
            while True:
                message = json.loads(self.ws.recv())
                if message.get("ticket") == ticket:
                    if message.get("event") == "error":
                        raise RuntimeError(message.get("message", message))
                    return message
                self.pending.append(message)
        finally:
            self.ws.settimeout(previous_timeout)

    def wait_event(self, names: set[str], timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            for index, message in enumerate(self.pending):
                if message.get("event") in names:
                    return self.pending.pop(index)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"timed out waiting for {sorted(names)}")
            previous_timeout = self.ws.gettimeout()
            self.ws.settimeout(remaining)
            try:
                message = json.loads(self.ws.recv())
            except WebSocketTimeoutException as exc:
                raise TimeoutError(f"timed out waiting for {sorted(names)}") from exc
            finally:
                self.ws.settimeout(previous_timeout)
            if message.get("event") in names:
                return message
            self.pending.append(message)

    def read(self, address: int, size: int) -> bytes:
        response = self.request(
            "memory.read", address=address, size=size, replacements=False
        )
        value = base64.b64decode(response["base64"])
        if len(value) != size:
            raise RuntimeError(
                f"short memory.read at 0x{address:08X}: expected {size}, got {len(value)}"
            )
        return value


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
        if not (address <= actual_int < address + size):
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


def ensure_running(session: Session) -> None:
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


def wait_for_our_hit(session: Session, address: int, size: int, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("no matching memory-breakpoint event before timeout")
        event = session.wait_event({"cpu.breakpoint.hit", "cpu.stepping"}, remaining)
        hit = event.get("hit")
        if breakpoint_matches(hit, address, size):
            return event

        if event.get("event") == "cpu.stepping":
            print(f"Ignoring unrelated cpu.stepping event (hit={hit!r}); resuming.")
            session.fire("cpu.resume")
            time.sleep(0.03)
        elif hit is not None:
            print(f"Ignoring unrelated breakpoint event: {hit}")


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture a real PPSSPP memory-breakpoint broadcast for a dialogue candidate.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--address", type=integer, default=0x0881C62C)
    parser.add_argument("--size", type=integer, default=4)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "debugger" / "dialogue-watch-line.json",
    )
    args = parser.parse_args()

    session = Session(args.host, args.port)
    armed = False
    game: dict[str, Any] | None = None
    baseline = b""
    modules: dict[str, Any] | None = None
    watched_disasm: dict[str, Any] | None = None
    armed_at: float | None = None
    try:
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

        session.request(
            "memory.breakpoint.add",
            address=args.address,
            size=args.size,
            enabled=True,
            log=True,
            read=False,
            write=False,
            change=True,
        )
        armed = True
        armed_at = time.monotonic()
        print("ARMED. Now advance exactly one textbox in PPSSPP.")
        matched_event = wait_for_our_hit(session, args.address, args.size, args.timeout)
        elapsed = time.monotonic() - armed_at

        hit = matched_event.get("hit") or {}
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
        try:
            regs_raw = session.request("cpu.getAllRegs")
            regs = compact_regs(regs_raw)
        except Exception as exc:
            print(f"WARNING: register capture failed: {exc}")

        backtrace: dict[str, Any] | None = None
        try:
            backtrace = session.request("hle.backtrace")
        except Exception as exc:
            print(f"WARNING: backtrace failed: {exc}")

        pc = int(hit.get("pc") or cpu_status.get("pc") or 0)
        try:
            pc_disasm = session.request(
                "memory.disasm", address=max(0x08000000, pc - 0x20), count=20,
                displaySymbols=True, compact=True,
            )
        except Exception as exc:
            pc_disasm = {"error": str(exc)}

        after = session.read(args.address, args.size)
        write_report(args.output, {
            "result": "hit",
            "game_status": game,
            "watch": {
                "address": f"0x{args.address:08X}",
                "size": args.size,
                "baseline_hex": baseline.hex().upper(),
                "after_hex": after.hex().upper(),
                "elapsed_seconds": elapsed,
            },
            "breakpoint_event": matched_event,
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
        print("If you advanced the textbox, this watched word was not touched by a matching memory breakpoint event.")
        try:
            after = session.read(args.address, args.size)
            after_hex = after.hex().upper()
        except Exception as read_exc:
            after_hex = None
            session.pending.append({"event": "probe.read_after_timeout.error", "message": str(read_exc)})
        elapsed = time.monotonic() - armed_at if armed_at is not None else None
        write_report(args.output, {
            "result": "timeout",
            "error": str(exc),
            "game_status": game,
            "watch": {
                "address": f"0x{args.address:08X}",
                "size": args.size,
                "baseline_hex": baseline.hex().upper(),
                "after_hex": after_hex,
                "elapsed_seconds": elapsed,
            },
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
