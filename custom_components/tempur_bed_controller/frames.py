"""Captured protocol frame tables with no Home Assistant dependency."""

from __future__ import annotations

# Each complete frame was observed in private pilot captures. The integration
# intentionally uses this table rather than an inferred checksum algorithm.
MASSAGE_LEVEL_ACTIONS: dict[str, tuple[bytes, ...]] = {
    "head": tuple(bytes.fromhex(value) for value in (
        "330532039485000011", "330532039485001809", "330532039485003021",
        "330532039485004859", "330532039485006071", "330532039485007869",
        "330532039485009081", "33053203948500A8B9", "33053203948500C0D1",
        "33053203948500D8C9", "33053203948500F0E1",
    )),
    "lumbar": tuple(bytes.fromhex(value) for value in (
        "330532039485010010", "330532039485011808", "330532039485013020",
        "330532039485014858", "330532039485016070", "330532039485017868",
        "330532039485019080", "33053203948501A8B8", "33053203948501C0D0",
        "33053203948501D8C8", "33053203948501F0E0",
    )),
    "leg": tuple(bytes.fromhex(value) for value in (
        "330532039485020013", "33053203948502180B", "330532039485023023",
        "33053203948502485B", "330532039485026073", "33053203948502786B",
        "330532039485029083", "33053203948502A8BB", "33053203948502C0D3",
        "33053203948502D8CB", "33053203948502F0E3",
    )),
}

LIFT_ACTIONS: dict[str, bytes] = {
    "head_up": bytes.fromhex("3305321894530005C2"),
    "head_down": bytes.fromhex("3305321894540005C5"),
    "leg_up": bytes.fromhex("3305321894510100C4"),
    "leg_down": bytes.fromhex("3305321894520100C7"),
    "flat": bytes.fromhex("33053203945C0400CC"),
}

MEMORY_ACTIONS: dict[str, bytes] = {
    "1": bytes.fromhex("33053203945C0000C8"),
    "2": bytes.fromhex("33053203945C0100C9"),
    "3": bytes.fromhex("33053203945C0200CA"),
    "4": bytes.fromhex("33053203945C0300CB"),
}

MASSAGE_MODE_ACTIONS: dict[str, bytes] = {
    "1": bytes.fromhex("33053203948D007861"),
    "2": bytes.fromhex("33053203948D017860"),
    "3": bytes.fromhex("33053203948D027863"),
    "4": bytes.fromhex("33053203948D037862"),
}

MASSAGE_STOP = bytes.fromhex("330532039486000012")
