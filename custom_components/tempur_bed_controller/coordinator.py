"""Controller state and action coordinator."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from homeassistant.exceptions import HomeAssistantError

from .const import LIFT_ACTIONS, MASSAGE_LEVEL_ACTIONS, MASSAGE_MODE_ACTIONS, MASSAGE_STOP, MEMORY_ACTIONS
from .protocol import massage_level_frame
from .transport import ControllerTimeoutError, ControllerTransport


class BedCoordinator:
    """Serialize actions and keep only transparent last-requested state."""

    def __init__(self, host: str, port: int, name: str, entry_id: str) -> None:
        self.transport = ControllerTransport(host, port)
        self.host = host
        self.port = port
        self.name = name
        self.entry_id = entry_id
        self.massage_levels: dict[str, int | None] = {zone: None for zone in MASSAGE_LEVEL_ACTIONS}
        self.last_memory: str | None = None
        self.last_massage_mode: str | None = None
        self.last_lift_actions: dict[str, str | None] = {"head": None, "leg": None}
        self._listeners: list[Callable[[], None]] = []
        self._action_lock = asyncio.Lock()

    @property
    def device_info(self) -> dict[str, object]:
        return {
            "identifiers": {("tempur_bed_controller", self.entry_id)},
            "name": self.name,
            "manufacturer": "Tempur-Pedic",
            "model": "UDP adjustable bed controller",
            "configuration_url": None,
        }

    async def async_setup(self) -> None:
        await self.transport.async_setup()

    async def async_close(self) -> None:
        await self.transport.async_close()

    async def async_reinitialize_session(self) -> None:
        """Re-open the controller session without issuing a bed action."""
        async with self._action_lock:
            try:
                await self.transport.async_reinitialize_session()
            except ControllerTimeoutError as err:
                raise HomeAssistantError(str(err)) from err

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def remove_listener() -> None:
            self._listeners.remove(listener)

        return remove_listener

    async def async_press(self, key: str) -> None:
        """Send one button action and update state only after ACK3."""
        async with self._action_lock:
            try:
                if key in LIFT_ACTIONS:
                    await self.transport.async_send_action(LIFT_ACTIONS[key], key)
                    if key == "flat":
                        self.last_lift_actions = {"head": "flat", "leg": "flat"}
                    else:
                        zone, _direction = key.split("_", maxsplit=1)
                        self.last_lift_actions[zone] = key
                elif key in MEMORY_ACTIONS:
                    await self.transport.async_send_action(MEMORY_ACTIONS[key], f"memory_{key}")
                    self.last_memory = key
                elif key.startswith("mode_") and key.removeprefix("mode_") in MASSAGE_MODE_ACTIONS:
                    mode = key.removeprefix("mode_")
                    await self.transport.async_send_action(MASSAGE_MODE_ACTIONS[mode], f"massage_mode_{mode}")
                    self.last_massage_mode = mode
                elif key == "massage_stop":
                    await self.transport.async_send_action(MASSAGE_STOP, "massage_stop")
                    self.last_massage_mode = None
                elif key.startswith("massage_") and key.endswith(("_more", "_less")):
                    _, zone, direction = key.split("_")
                    await self._async_adjust_massage(zone, direction)
                    return
                else:
                    raise HomeAssistantError(f"Unsupported action: {key}")
            except ControllerTimeoutError as err:
                raise HomeAssistantError(str(err)) from err
            self._notify_listeners()

    async def async_set_massage_level(self, zone: str, level: int) -> None:
        """Request one exact massage level and remember it after ACK3."""
        async with self._action_lock:
            await self._async_set_massage_level(zone, level)

    async def _async_set_massage_level(self, zone: str, level: int) -> None:
        try:
            await self.transport.async_send_action(
                massage_level_frame(zone, level), f"massage_{zone}_level_{level}"
            )
        except (ControllerTimeoutError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        self.massage_levels[zone] = level
        self._notify_listeners()

    async def async_adjust_massage(self, zone: str, direction: str) -> None:
        """Move from the last requested level by one exact protocol level."""
        async with self._action_lock:
            await self._async_adjust_massage(zone, direction)

    async def _async_adjust_massage(self, zone: str, direction: str) -> None:
        current = self.massage_levels[zone]
        if current is None:
            raise HomeAssistantError(
                f"{zone.title()} massage level is unknown. Set an explicit level first."
            )
        target = min(10, current + 1) if direction == "more" else max(0, current - 1)
        await self._async_set_massage_level(zone, target)

    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()
