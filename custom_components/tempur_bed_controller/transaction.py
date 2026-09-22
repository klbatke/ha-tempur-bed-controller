"""Pure, capture-backed controller transaction rules."""

from __future__ import annotations

ACTION_ACK = b"ACK3"
ACTION_FRAME_LENGTH = 9


def direct_action_datagrams(frame: bytes) -> tuple[bytes, ...]:
    """Return the single observed direct datagram for an HA action.

    A supplied iPad trace showed the controller accepting a direct nine-byte
    command and returning ``ACK3``. It did not establish a generic opener,
    delay, repeat count, or release command. Keep this deliberately narrow.
    """
    if len(frame) != ACTION_FRAME_LENGTH:
        raise ValueError("Controller action frame must be exactly 9 bytes")
    return (frame,)
