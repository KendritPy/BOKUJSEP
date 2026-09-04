#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import ctypes
import json
import logging
from logging.handlers import RotatingFileHandler
import sys
import time
from pathlib import Path
from typing import Any, Callable

from websocket import WebSocketTimeoutException, create_connection


class PPSSPPDebugger:
    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self.url = f"ws://{host}:{port}/debugger"
        self.ws = create_connection(
            self.url,
            subprotocols=["debugger.ppsspp.org"],
            timeout=timeout,
            suppress_origin=True,
        )
        self.ticket = 0
        self.pending: list[dict[str, Any]] = []
        self.request("version", name="BokuLangToggle", version="0.1")
        # PPSSPP 1.20.4 calls this broadcast.config.set (not
        # client.config.set.)  Explicitly keep stepping broadcasts enabled;
        # memory-breakpoint hits are reported through cpu.stepping in 1.20.4.
        # High-rate analog input broadcasts share this socket and can crowd out
        # the brief debugger events a writer probe needs.
        self.request(
            "broadcast.config.set",
            disallowed={
                "stepping": False,
                "logger": False,
                "input": True,
                "game": True,
            },
        )

    def close(self) -> None:
        self.ws.close()

    def send(self, event: str, **parameters: Any) -> int:
        self.ticket += 1
        self.ws.send(json.dumps({"event": event, "ticket": self.ticket, **parameters}))
        return self.ticket

    def _recv(self, timeout: float | None = None) -> dict[str, Any]:
        previous_timeout = self.ws.gettimeout()
        if timeout is not None:
            self.ws.settimeout(timeout)
        try:
            message = json.loads(self.ws.recv())
        finally:
            self.ws.settimeout(previous_timeout)
        if not isinstance(message, dict):
            raise RuntimeError(f"PPSSPP returned a non-object message: {message!r}")
        return message

    def request(self, event: str, timeout: float | None = None, **parameters: Any) -> dict[str, Any]:
        ticket = self.send(event, **parameters)
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                raise WebSocketTimeoutException(f"timed out waiting for ticket {ticket}")
            message = self._recv(remaining)
            if message.get("ticket") != ticket:
                self.pending.append(message)
                continue
            if message.get("event") == "error":
                raise RuntimeError(message.get("message", message))
            return message

    def fire(self, event: str, **parameters: Any) -> None:
        self.ws.send(json.dumps({"event": event, **parameters}))

    def wait_event(
        self,
        names: set[str],
        timeout: float,
        predicate: Callable[[dict[str, Any]], bool] | None = None,
    ) -> dict[str, Any]:
        """Wait for a broadcast without losing interleaved messages.

        Requests and broadcasts share one WebSocket.  request() queues every
        message whose ticket does not match; wait_event() consumes a matching
        queued broadcast first, then continues receiving while preserving all
        unrelated traffic.
        """
        matches = predicate or (lambda _message: True)
        deadline = time.monotonic() + timeout
        while True:
            for index, message in enumerate(self.pending):
                if message.get("event") in names and matches(message):
                    return self.pending.pop(index)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"timed out waiting for {sorted(names)}")
            try:
                message = self._recv(remaining)
            except WebSocketTimeoutException as exc:
                raise TimeoutError(f"timed out waiting for {sorted(names)}") from exc
            if message.get("event") in names and matches(message):
                return message
            self.pending.append(message)

    def read(self, address: int, size: int, *, replacements: bool = False) -> bytes:
        """Read guest bytes exactly as stored in PSP memory.

        PPSSPP's memory.read defaults replacements=true, which may expose emulator
        replacement/emuhack opcodes in executable pages. Reverse-engineering RAM
        snapshots need replacements=false or unchanged game code can appear to mutate.
        """
        result = self.request(
            "memory.read", address=address, size=size, replacements=replacements
        )
        value = base64.b64decode(result["base64"])
        if len(value) != size:
            raise RuntimeError(
                f"short memory.read at 0x{address:08X}: expected {size} bytes, got {len(value)}"
            )
        return value

    def write(self, address: int, value: bytes) -> None:
        self.request("memory.write", address=address, base64=base64.b64encode(value).decode("ascii"))

    def search(self, pattern: bytes, address: int = 0x08000000, size: int = 0x02000000) -> dict[str, Any]:
        try:
            return self.request(
                "memory.search", address=address, size=size, type="bytes",
                base64=base64.b64encode(pattern).decode("ascii"), align=1, maxResults=10000,
            )
        except RuntimeError as error:
            if "unknown event" not in str(error):
                raise

        # PPSSPP 1.20.4 has memory.read but predates memory.search. Read RAM in
        # bounded chunks and retain an overlap so matches crossing a boundary
        # are not missed.
        if not pattern:
            raise ValueError("search pattern cannot be empty")
        results: list[int] = []
        chunk_size = 0x100000
        overlap = len(pattern) - 1
        cursor = address
        end = address + size
        tail = b""
        while cursor < end:
            current_size = min(chunk_size, end - cursor)
            current = self.read(cursor, current_size)
            haystack = tail + current
            base = cursor - len(tail)
            start = 0
            while True:
                found = haystack.find(pattern, start)
                if found < 0:
                    break
                match_address = base + found
                if address <= match_address < end:
                    results.append(match_address)
                start = found + 1
            tail = haystack[-overlap:] if overlap else b""
            cursor += current_size
        return {
            "event": "memory.search.local",
            "address": address,
            "size": size,
            "results": results,
        }


def integer(value: str) -> int:
    return int(value, 0)


HOTKEYS = {
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
}


# Names accepted by PPSSPP's input.buttons.press event. The plugin config uses
# the corresponding PSP names (LTRIGGER/RTRIGGER rather than L/R), so this
# mapping also keeps the host-side F7 bridge aligned with the guest setting.
GUEST_BUTTONS = {
    "l": "ltrigger",
    "r": "rtrigger",
    "select": "select",
    "start": "start",
    "up": "up",
    "right": "right",
    "down": "down",
    "left": "left",
    "ltrigger": "ltrigger",
    "rtrigger": "rtrigger",
    "l2": "l2",
    "l3": "l3",
    "r2": "r2",
    "r3": "r3",
    "triangle": "triangle",
    "circle": "circle",
    "cross": "cross",
    "square": "square",
    "home": "home",
    "hold": "hold",
    "note": "note",
    "screen": "screen",
    "volup": "vol_up",
    "voldown": "vol_down",
    "wlanup": "wlan",
    "wlan": "wlan",
    "remote": "remote_hold",
    "remotehold": "remote_hold",
    "disc": "disc",
    "ms": "memstick",
    "memstick": "memstick",
}


def guest_button(value: str) -> str:
    normalized = value.strip().lower().replace("_", "")
    if normalized not in GUEST_BUTTONS:
        choices = ", ".join(sorted(GUEST_BUTTONS))
        raise argparse.ArgumentTypeError(
            f"unsupported guest button {value!r}; choose one of: {choices}"
        )
    return GUEST_BUTTONS[normalized]


def send_toggle(debugger: PPSSPPDebugger, button_name: str) -> dict[str, Any]:
    # Three frames cover the guest's 16 ms polling interval even when the
    # host request arrives near a controller sampling boundary.
    return debugger.request("input.buttons.press", timeout=3.0, button=button_name, duration=3)


def run_hotkey(host: str, port: int, key_name: str, button_name: str) -> None:
    if not hasattr(ctypes, "windll"):
        raise SystemExit("the host hotkey helper currently targets Windows")
    get_key = ctypes.windll.user32.GetAsyncKeyState
    previous = False
    vk = HOTKEYS[key_name]
    debugger = None
    next_health_check = 0.0
    logging.info("Bridge started: %s -> guest %s, %s:%s", key_name, button_name, host, port)
    try:
        while True:
            current = bool(get_key(vk) & 0x8000)
            pressed = current and not previous
            previous = current
            try:
                if debugger is None:
                    debugger = PPSSPPDebugger(host, port)
                    logging.info("Debugger connected")
                    next_health_check = 0.0
                if pressed:
                    logging.info("%s detected; sending guest %s", key_name, button_name)
                    send_toggle(debugger, button_name)
                    logging.info("PPSSPP acknowledged input (guest application is recorded in plugin log)")
                if time.monotonic() >= next_health_check:
                    debugger.request("game.status", timeout=3.0)
                    debugger.pending.clear()
                    next_health_check = time.monotonic() + 5.0
            except Exception:
                logging.exception("Debugger operation failed; reconnecting, without replaying input")
                if debugger is not None:
                    debugger.close()
                    debugger = None
                time.sleep(1)
            time.sleep(1 / 120)
    finally:
        if debugger is not None:
            debugger.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="PPSSPP WebSocket debugger client for BokuLangToggle")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    raw = commands.add_parser("event")
    raw.add_argument("name")
    raw.add_argument("json", nargs="?", default="{}")
    raw.add_argument("--output", type=Path)
    read = commands.add_parser("read")
    read.add_argument("address", type=integer)
    read.add_argument("size", type=integer)
    read.add_argument("--output", type=Path)
    write = commands.add_parser("write")
    write.add_argument("address", type=integer)
    write.add_argument("hex")
    search = commands.add_parser("search")
    search.add_argument("hex")
    search.add_argument("--address", type=integer, default=0x08000000)
    search.add_argument("--size", type=integer, default=0x02000000)
    memcheck = commands.add_parser("memcheck")
    memcheck.add_argument("address", type=integer)
    memcheck.add_argument("size", type=integer)
    memcheck.add_argument("--write", action="store_true")
    commands.add_parser("pause")
    commands.add_parser("resume")
    commands.add_parser("regs")
    toggle = commands.add_parser("toggle")
    toggle.add_argument("--button", type=guest_button, default="note")
    press = commands.add_parser("press")
    press.add_argument("button")
    press.add_argument("--duration", type=int, default=1)
    screenshot = commands.add_parser("screenshot")
    screenshot.add_argument("output", type=Path)
    hotkey = commands.add_parser("hotkey")
    hotkey.add_argument(
        "--key", choices=sorted(HOTKEYS), default="F7",
        help="unassigned PPSSPP keyboard key to use (default: F7)",
    )
    hotkey.add_argument(
        "--button", type=guest_button, default="note",
        help="guest PSP control to press when the hotkey is detected (default: note)",
    )
    hotkey.add_argument("--log-file", type=Path,
                        default=Path(__file__).resolve().parents[1] / "build/logs/hotkey.log")
    args = parser.parse_args()

    if args.command == "hotkey":
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s",
                            handlers=[RotatingFileHandler(args.log_file, maxBytes=1000000,
                                                         backupCount=2, encoding="utf-8")])
        try:
            run_hotkey(args.host, args.port, args.key, args.button)
        except Exception:
            logging.exception("Hotkey bridge stopped unexpectedly")
            raise
        return

    debugger = PPSSPPDebugger(args.host, args.port)
    try:
        if args.command == "status":
            output = debugger.request("game.status")
        elif args.command == "event":
            output = debugger.request(args.name, **json.loads(args.json))
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                output = {"event": output.get("event"), "output": str(args.output)}
        elif args.command == "read":
            value = debugger.read(args.address, args.size)
            if args.output:
                args.output.write_bytes(value)
                output = {"output": str(args.output), "size": len(value)}
            else:
                output = {"address": args.address, "hex": value.hex().upper()}
        elif args.command == "write":
            value = bytes.fromhex(args.hex)
            debugger.write(args.address, value)
            output = {"address": args.address, "size": len(value)}
        elif args.command == "search":
            output = debugger.search(bytes.fromhex(args.hex), args.address, args.size)
        elif args.command == "memcheck":
            output = debugger.request(
                "memory.breakpoint.add", address=args.address, size=args.size,
                read=not args.write, write=args.write, enabled=True, log=True,
            )
        elif args.command == "pause":
            debugger.fire("cpu.stepping")
            output = {"accepted": True}
        elif args.command == "resume":
            debugger.fire("cpu.resume")
            output = {"accepted": True}
        elif args.command == "regs":
            output = debugger.request("cpu.getAllRegs")
        elif args.command == "toggle":
            output = send_toggle(debugger, args.button)
        elif args.command == "press":
            output = debugger.request("input.buttons.press", button=args.button, duration=args.duration)
        elif args.command == "screenshot":
            debugger.fire("cpu.stepping")
            debugger.wait_event({"cpu.stepping"}, 5.0)
            try:
                response = debugger.request("gpu.buffer.screenshot")
            finally:
                # A failed GPU readback must never leave the game paused.
                debugger.fire("cpu.resume")
            prefix = "data:image/png;base64,"
            if not response.get("uri", "").startswith(prefix):
                raise RuntimeError("PPSSPP returned an unexpected screenshot payload")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(base64.b64decode(response["uri"][len(prefix):]))
            output = {"output": str(args.output), "width": response.get("width"), "height": response.get("height")}
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except WebSocketTimeoutException as exc:
        raise SystemExit(f"debugger timed out: {exc}") from exc
    finally:
        debugger.close()


if __name__ == "__main__":
    main()
