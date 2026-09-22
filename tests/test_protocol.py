"""Protocol-table tests that require no Home Assistant installation."""

from __future__ import annotations

import runpy
import unittest
from pathlib import Path

FRAMES = runpy.run_path(
    Path(__file__).parents[1] / "custom_components" / "tempur_bed_controller" / "frames.py"
)
MASSAGE_LEVEL_ACTIONS = FRAMES["MASSAGE_LEVEL_ACTIONS"]
LIFT_ACTIONS = FRAMES["LIFT_ACTIONS"]
MEMORY_ACTIONS = FRAMES["MEMORY_ACTIONS"]
MASSAGE_MODE_ACTIONS = FRAMES["MASSAGE_MODE_ACTIONS"]
MASSAGE_STOP = FRAMES["MASSAGE_STOP"]
TRANSACTION = runpy.run_path(
    Path(__file__).parents[1] / "custom_components" / "tempur_bed_controller" / "transaction.py"
)
ACTION_ACK = TRANSACTION["ACTION_ACK"]
OPEN_FRAME = TRANSACTION["OPEN_FRAME"]
OPEN_ACK = TRANSACTION["OPEN_ACK"]
session_open_datagram = TRANSACTION["session_open_datagram"]
direct_action_datagrams = TRANSACTION["direct_action_datagrams"]
SESSION_ACTION_SETTLE_SECONDS = TRANSACTION["SESSION_ACTION_SETTLE_SECONDS"]


def massage_level_frame(zone: str, level: int) -> bytes:
    if zone not in MASSAGE_LEVEL_ACTIONS:
        raise ValueError(f"Unsupported massage zone: {zone}")
    if not 0 <= level <= 10:
        raise ValueError("Massage level must be between 0 and 10")
    return MASSAGE_LEVEL_ACTIONS[zone][level]


class TestMassageProtocol(unittest.TestCase):
    def test_session_open_frame_and_ack_are_capture_backed(self) -> None:
        self.assertEqual(session_open_datagram(), bytes.fromhex("fe4c4f474943444154414f50454e"))
        self.assertEqual(OPEN_FRAME, session_open_datagram())
        self.assertEqual(OPEN_ACK, b"ACK\xfe")

    def test_session_settle_interval_is_short_and_capture_derived(self) -> None:
        self.assertGreaterEqual(SESSION_ACTION_SETTLE_SECONDS, 0.005)
        self.assertLess(SESSION_ACTION_SETTLE_SECONDS, 0.050)

    def test_direct_transaction_is_one_captured_action_and_ack3(self) -> None:
        frame = bytes.fromhex("3305321894530005c2")
        self.assertEqual(direct_action_datagrams(frame), (frame,))
        self.assertEqual(ACTION_ACK, b"ACK3")

    def test_direct_transaction_rejects_non_action_datagrams(self) -> None:
        with self.assertRaises(ValueError):
            direct_action_datagrams(b"LOGICDATAOPEN")

    def test_every_zone_has_eleven_complete_frames(self) -> None:
        for zone, frames in MASSAGE_LEVEL_ACTIONS.items():
            with self.subTest(zone=zone):
                self.assertEqual(len(frames), 11)
                self.assertTrue(all(len(frame) == 9 for frame in frames))

    def test_exact_level_lookup(self) -> None:
        self.assertEqual(massage_level_frame("head", 0).hex(), "330532039485000011")
        self.assertEqual(massage_level_frame("lumbar", 5).hex(), "330532039485017868")
        self.assertEqual(massage_level_frame("leg", 10).hex(), "33053203948502f0e3")

    def test_invalid_level_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            massage_level_frame("head", 11)

    def test_invalid_zone_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            massage_level_frame("foot", 0)

    def test_all_twenty_button_actions_are_complete_frames(self) -> None:
        actions = (
            *LIFT_ACTIONS.values(),
            *MEMORY_ACTIONS.values(),
            *(MASSAGE_LEVEL_ACTIONS[zone][1] for zone in MASSAGE_LEVEL_ACTIONS),
            *(MASSAGE_LEVEL_ACTIONS[zone][0] for zone in MASSAGE_LEVEL_ACTIONS),
            *MASSAGE_MODE_ACTIONS.values(),
            MASSAGE_STOP,
        )
        self.assertEqual(len(actions), 20)
        self.assertTrue(all(len(action) == 9 for action in actions))
