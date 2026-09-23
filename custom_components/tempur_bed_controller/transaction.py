"""Pure, capture-backed controller transaction rules."""

from __future__ import annotations

from ipaddress import ip_address

ACTION_ACK = b"ACK3"
OPEN_FRAME = bytes.fromhex("FE4C4F474943444154414F50454E")
OPEN_ACK = b"ACK\xfe"
ACTION_FRAME_LENGTH = 9
# The iPad traces show 4.6-7.0 ms between ACKFE and the first action.
SESSION_ACTION_SETTLE_SECONDS = 0.010
# A controller session acknowledged a command after 170 seconds of inactivity,
# but did not acknowledge after 206 seconds. Reopen conservatively before the
# next explicit action after two idle minutes.
SESSION_IDLE_REOPEN_SECONDS = 120.0
# User-initiated repeated actions are serialized with this post-ACK holdoff.
# It is an integration safety cadence, not a claimed wire-protocol delay.
REPEATED_ACTION_INTERVAL_SECONDS = 0.500


def session_open_datagram() -> bytes:
    """Return the captured LogicData session-open datagram."""
    return OPEN_FRAME


def session_requires_reopen(last_action_ack: float | None, now: float) -> bool:
    """Return whether an idle controller session should be reopened."""
    return (
        last_action_ack is not None
        and now - last_action_ack >= SESSION_IDLE_REOPEN_SECONDS
    )


def acknowledgement_matches(response: bytes, expected: bytes) -> bool:
    """Return whether a controller response has the expected acknowledgement."""
    return response.startswith(expected)


def controller_source_matches(
    configured_host: str, configured_port: int, addr: tuple[str, int]
) -> bool:
    """Validate a response endpoint against the configured controller."""
    if addr[1] != configured_port:
        return False
    try:
        return ip_address(addr[0]) == ip_address(configured_host)
    except ValueError:
        # A connected UDP endpoint already restricts the peer when a hostname
        # was configured; the port check remains useful for the queued reply.
        return True


def direct_action_datagrams(frame: bytes) -> tuple[bytes, ...]:
    """Return the single observed direct datagram for an HA action.

    Supplied iPad traces show a direct nine-byte command returning ``ACK3``.
    Session initialization is deliberately kept separate so the transport can
    send it once rather than prepending it to every action.
    """
    if len(frame) != ACTION_FRAME_LENGTH:
        raise ValueError("Controller action frame must be exactly 9 bytes")
    return (frame,)
