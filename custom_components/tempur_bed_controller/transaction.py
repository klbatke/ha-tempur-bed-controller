"""Pure, capture-backed controller transaction rules."""

from __future__ import annotations

ACTION_ACK = b"ACK3"
OPEN_FRAME = bytes.fromhex("FE4C4F474943444154414F50454E")
OPEN_ACK = b"ACK\xfe"
ACTION_FRAME_LENGTH = 9


def session_open_datagram() -> bytes:
    """Return the captured LogicData session-open datagram."""
    return OPEN_FRAME


def direct_action_datagrams(frame: bytes) -> tuple[bytes, ...]:
    """Return the single observed direct datagram for an HA action.

    Supplied iPad traces show a direct nine-byte command returning ``ACK3``.
    Session initialization is deliberately kept separate so the transport can
    send it once rather than prepending it to every action.
    """
    if len(frame) != ACTION_FRAME_LENGTH:
        raise ValueError("Controller action frame must be exactly 9 bytes")
    return (frame,)
