"""Constants for the Tempur Bed Controller integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, Platform

from .frames import (
    LIFT_ACTIONS,
    MASSAGE_LEVEL_ACTIONS,
    MASSAGE_MODE_ACTIONS,
    MASSAGE_STOP,
    MEMORY_ACTIONS,
)

DOMAIN = "tempur_bed_controller"
DEFAULT_NAME = "Bed Controller"
DEFAULT_PORT = 50007
PLATFORMS: tuple[Platform, ...] = (
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
)

CONF_HOST = CONF_HOST
CONF_NAME = CONF_NAME
CONF_PORT = CONF_PORT

OPEN_FRAME = bytes.fromhex("FE4C4F474943444154414F50454E")
ACK_OPEN = b"ACK\xfe"
ACK_ACTION = b"ACK3"
ACK_TIMEOUT_SECONDS = 2.0
ACTION_DELAY_SECONDS = 0.5

MASSAGE_ZONES = tuple(MASSAGE_LEVEL_ACTIONS)
UNKNOWN_OPTION = "Unknown"
