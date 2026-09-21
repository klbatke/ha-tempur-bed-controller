"""Pure protocol helpers for the captured UDP controller protocol."""

from __future__ import annotations

from .frames import MASSAGE_LEVEL_ACTIONS


def massage_level_frame(zone: str, level: int) -> bytes:
    """Return the captured action frame for an exact massage level."""
    if zone not in MASSAGE_LEVEL_ACTIONS:
        raise ValueError(f"Unsupported massage zone: {zone}")
    if not 0 <= level <= 10:
        raise ValueError("Massage level must be between 0 and 10")
    return MASSAGE_LEVEL_ACTIONS[zone][level]
