from __future__ import annotations

import base64
import json
import sys
import unittest
from argparse import ArgumentTypeError
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace

from websocket import WebSocketTimeoutException


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from ppsspp_debug import PPSSPPDebugger, guest_button, send_toggle, run_hotkey  # noqa: E402


class FakeWebSocket:
    def __init__(self, messages: list[dict[str, object] | BaseException]):
        self.messages = list(messages)
        self.sent: list[dict[str, object]] = []
        self.timeout = 5.0
        self.closed = False

    def send(self, value: str) -> None:
        self.sent.append(json.loads(value))

    def recv(self) -> str:
        if not self.messages:
            raise AssertionError("fake WebSocket ran out of messages")
        message = self.messages.pop(0)
        if isinstance(message, BaseException):
            raise message
        return json.dumps(message)

    def gettimeout(self) -> float:
        return self.timeout

    def settimeout(self, value: float) -> None:
        self.timeout = value

    def close(self) -> None:
        self.closed = True


def connected(messages: list[dict[str, object] | BaseException]) -> tuple[PPSSPPDebugger, FakeWebSocket]:
    websocket = FakeWebSocket(
        [
            {"event": "version", "ticket": 1, "name": "PPSSPP", "version": "v1.20.4"},
            {"event": "broadcast.config.set", "ticket": 2, "disallowed": {}},
            *messages,
        ]
    )
    with patch("ppsspp_debug.create_connection", return_value=websocket):
        debugger = PPSSPPDebugger("127.0.0.1", 8765)
    return debugger, websocket


class PPSSPPDebuggerTests(unittest.TestCase):
    def test_bridge_reconnect_does_not_repeat_held_toggle(self) -> None:
        first = Mock(pending=[])
        first.request.side_effect = RuntimeError("connection lost after input")
        second = Mock(pending=[])
        keys = Mock(side_effect=[0x8000, 0x8000, 0, 0x8000, KeyboardInterrupt])
        fake_windows = SimpleNamespace(user32=SimpleNamespace(GetAsyncKeyState=keys))
        with patch("ppsspp_debug.ctypes.windll", fake_windows, create=True), \
             patch("ppsspp_debug.PPSSPPDebugger", side_effect=[first, second]), \
             patch("ppsspp_debug.time.sleep"), self.assertLogs(level="INFO"):
            with self.assertRaises(KeyboardInterrupt):
                run_hotkey("127.0.0.1", 8765, "F7", "note")
        first.request.assert_called_once_with(
            "input.buttons.press", timeout=3.0, button="note", duration=3)
        presses = [c for c in second.request.call_args_list
                   if c.args[0] == "input.buttons.press"]
        self.assertEqual(len(presses), 1)
        first.close.assert_called_once()
        second.close.assert_called_once()

    def test_toggle_waits_for_acknowledgement_and_spans_guest_poll(self) -> None:
        debugger, websocket = connected([
            {"event": "input.buttons.press", "ticket": 3},
        ])
        self.assertEqual(send_toggle(debugger, "note")["event"], "input.buttons.press")
        self.assertEqual(websocket.sent[-1], {
            "event": "input.buttons.press", "ticket": 3,
            "button": "note", "duration": 3,
        })

    def test_toggle_reports_rejection_without_replaying_press(self) -> None:
        debugger, websocket = connected([
            {"event": "error", "ticket": 3, "message": "game is not running"},
        ])
        with self.assertRaisesRegex(RuntimeError, "game is not running"):
            send_toggle(debugger, "note")
        self.assertEqual(len(websocket.sent), 3)

    def test_guest_button_names_match_ppsspp_controls(self) -> None:
        self.assertEqual(guest_button("NOTE"), "note")
        self.assertEqual(guest_button("L_TRIGGER"), "ltrigger")
        self.assertEqual(guest_button("VOL_UP"), "vol_up")
        self.assertEqual(guest_button("L"), "ltrigger")
        self.assertEqual(guest_button("R"), "rtrigger")
        for button in ("L2", "L3", "R2", "R3"):
            self.assertEqual(guest_button(button), button.lower())

        with self.assertRaises(ArgumentTypeError):
            guest_button("joystick-button-7")

    def test_identifies_and_enables_stepping_broadcasts(self) -> None:
        debugger, websocket = connected([])

        self.assertEqual(websocket.sent[0]["event"], "version")
        self.assertEqual(
            websocket.sent[1],
            {
                "event": "broadcast.config.set",
                "ticket": 2,
                "disallowed": {
                    "stepping": False,
                    "logger": False,
                    "input": True,
                    "game": True,
                },
            },
        )
        debugger.close()
        self.assertTrue(websocket.closed)

    def test_request_preserves_interleaved_broadcasts(self) -> None:
        debugger, _websocket = connected(
            [
                {
                    "event": "cpu.stepping",
                    "pc": 0x08812340,
                    "reason": "memory.breakpoint",
                    "relatedAddress": 0x0892EBA4,
                },
                {"event": "cpu.resume"},
                {"event": "cpu.status", "ticket": 3, "stepping": True},
            ]
        )

        response = debugger.request("cpu.status")

        self.assertTrue(response["stepping"])
        hit = debugger.wait_event({"cpu.stepping"}, 0.1)
        self.assertEqual(hit["relatedAddress"], 0x0892EBA4)
        self.assertEqual(debugger.pending, [{"event": "cpu.resume"}])

    def test_wait_event_preserves_unmatched_socket_messages(self) -> None:
        debugger, _websocket = connected(
            [
                {"event": "game.status", "game": {"id": "UCJS10038"}},
                {"event": "cpu.stepping", "reason": "cpu.stepping"},
            ]
        )

        event = debugger.wait_event({"cpu.stepping"}, 0.1)

        self.assertEqual(event["reason"], "cpu.stepping")
        self.assertEqual(debugger.pending[0]["event"], "game.status")

    def test_timeout_is_restored_after_request_error(self) -> None:
        debugger, websocket = connected([WebSocketTimeoutException("late")])
        websocket.timeout = 7.5

        with self.assertRaises(WebSocketTimeoutException):
            debugger.request("game.status", timeout=0.25)

        self.assertEqual(websocket.timeout, 7.5)

    def test_read_disables_replacements_and_checks_length(self) -> None:
        debugger, websocket = connected(
            [
                {
                    "event": "memory.read",
                    "ticket": 3,
                    "base64": base64.b64encode(b"\x01\x02").decode("ascii"),
                }
            ]
        )

        self.assertEqual(debugger.read(0x08800000, 2), b"\x01\x02")
        self.assertFalse(websocket.sent[-1]["replacements"])


if __name__ == "__main__":
    unittest.main()
