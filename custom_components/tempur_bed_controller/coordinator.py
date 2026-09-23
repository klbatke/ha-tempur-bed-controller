"""Controller state and acknowledged massage safety coordination."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import LIFT_ACTIONS, MASSAGE_LEVEL_ACTIONS, MASSAGE_MODE_ACTIONS, MASSAGE_STOP, MEMORY_ACTIONS
from .protocol import massage_level_frame
from .transaction import MASSAGE_AUTO_STOP_SECONDS
from .transport import ControllerTimeoutError, ControllerTransport

_LOGGER = logging.getLogger(__name__)


class BedCoordinator:
    """Serialize bed commands and maintain only acknowledged requested state."""

    def __init__(
        self, hass: HomeAssistant, host: str, port: int, name: str, entry_id: str
    ) -> None:
        self.hass = hass
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
        self._massage_resync_required = True
        self._massage_safety_state = "resynchronizing"
        self._massage_auto_stop_handle: asyncio.TimerHandle | None = None
        self._massage_resync_task: asyncio.Task[None] | None = None

    @property
    def device_info(self) -> dict[str, object]:
        return {
            "identifiers": {("tempur_bed_controller", self.entry_id)},
            "name": self.name,
            "manufacturer": "Tempur-Pedic",
            "model": "UDP adjustable bed controller",
            "configuration_url": None,
        }

    @property
    def massage_controls_available(self) -> bool:
        """Return whether acknowledged Stop established the zero baseline."""
        return not self._massage_resync_required

    @property
    def massage_safety_state(self) -> str:
        """Return a transparent integration-safety state, not bed telemetry."""
        return self._massage_safety_state

    async def async_setup(self) -> None:
        """Set up the UDP transport."""
        await self.transport.async_setup()

    async def async_close(self) -> None:
        """Cancel safety work and close the UDP transport."""
        self._cancel_massage_auto_stop()
        if self._massage_resync_task is not None:
            self._massage_resync_task.cancel()
        await self.transport.async_close()

    async def async_initialize_massage_safety(self) -> bool:
        """Send one Stop at integration startup to establish known level zero."""
        self._massage_resync_required = True
        self._massage_safety_state = "resynchronizing"
        self._cancel_massage_auto_stop()
        async with self._action_lock:
            try:
                await self._async_stop_massage("startup_massage_stop")
            except ControllerTimeoutError as err:
                _LOGGER.warning("Startup massage Stop was not confirmed: %s", err)
                return False
        return True

    async def async_reinitialize_session(self) -> None:
        """Re-open the controller session without issuing a bed action."""
        async with self._action_lock:
            try:
                await self.transport.async_reinitialize_session()
            except ControllerTimeoutError as err:
                raise HomeAssistantError(str(err)) from err

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an entity-state listener."""
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
                    self._require_massage_controls()
                    mode = key.removeprefix("mode_")
                    await self.transport.async_send_action(
                        MASSAGE_MODE_ACTIONS[mode], f"massage_mode_{mode}"
                    )
                    self.last_massage_mode = mode
                    self._arm_massage_auto_stop()
                elif key == "massage_stop":
                    await self._async_stop_massage("massage_stop")
                elif key.startswith("massage_") and key.endswith(("_more", "_less")):
                    _, zone, direction = key.split("_")
                    await self._async_adjust_massage(zone, direction)
                    return
                else:
                    raise HomeAssistantError(f"Unsupported action: {key}")
            except ControllerTimeoutError as err:
                if key != "massage_stop" and self._is_massage_key(key):
                    self._schedule_massage_resync("unacknowledged massage action")
                raise HomeAssistantError(str(err)) from err
            self._notify_listeners()

    async def async_set_massage_level(self, zone: str, level: int) -> None:
        """Request one exact massage level and remember it after ACK3."""
        async with self._action_lock:
            await self._async_set_massage_level(zone, level)

    async def _async_set_massage_level(self, zone: str, level: int) -> None:
        self._require_massage_controls()
        try:
            await self.transport.async_send_action(
                massage_level_frame(zone, level), f"massage_{zone}_level_{level}"
            )
        except (ControllerTimeoutError, ValueError) as err:
            if isinstance(err, ControllerTimeoutError):
                self._schedule_massage_resync("unacknowledged massage level")
            raise HomeAssistantError(str(err)) from err
        self.massage_levels[zone] = level
        if level > 0:
            self._arm_massage_auto_stop()
        self._notify_listeners()

    async def async_adjust_massage(self, zone: str, direction: str) -> None:
        """Move from the acknowledged requested level by one exact level."""
        async with self._action_lock:
            await self._async_adjust_massage(zone, direction)

    async def _async_adjust_massage(self, zone: str, direction: str) -> None:
        self._require_massage_controls()
        current = self.massage_levels[zone]
        if current is None:
            self._schedule_massage_resync("missing massage baseline")
            raise HomeAssistantError("Massage is resynchronizing; wait for Massage Stop acknowledgement.")
        target = min(10, current + 1) if direction == "more" else max(0, current - 1)
        await self._async_set_massage_level(zone, target)

    def _require_massage_controls(self) -> None:
        """Reject massage start/change commands until Stop establishes baseline."""
        if self._massage_resync_required:
            raise HomeAssistantError(
                "Massage is resynchronizing; wait for Massage Stop acknowledgement."
            )

    @staticmethod
    def _is_massage_key(key: str) -> bool:
        return key.startswith("massage_") or key.startswith("mode_")

    async def _async_stop_massage(self, action_name: str) -> None:
        """Stop massage and establish level zero only after ACK3."""
        try:
            await self.transport.async_send_action(MASSAGE_STOP, action_name)
        except ControllerTimeoutError:
            self._massage_resync_required = True
            self._massage_safety_state = "stop_not_confirmed"
            self._cancel_massage_auto_stop()
            self._notify_listeners()
            raise
        self.massage_levels = {zone: 0 for zone in MASSAGE_LEVEL_ACTIONS}
        self.last_massage_mode = None
        self._massage_resync_required = False
        self._massage_safety_state = "stopped"
        self._cancel_massage_auto_stop()
        self._notify_listeners()

    def _arm_massage_auto_stop(self) -> None:
        """Reset the 30-minute safety timer after acknowledged active massage."""
        self._cancel_massage_auto_stop()
        self._massage_safety_state = "auto_stop_scheduled"
        self._massage_auto_stop_handle = asyncio.get_running_loop().call_later(
            MASSAGE_AUTO_STOP_SECONDS, self._schedule_auto_stop
        )

    def _cancel_massage_auto_stop(self) -> None:
        """Cancel a pending massage safety Stop, if any."""
        if self._massage_auto_stop_handle is not None:
            self._massage_auto_stop_handle.cancel()
            self._massage_auto_stop_handle = None

    def _schedule_auto_stop(self) -> None:
        """Queue the automatic Stop after the safety interval."""
        self._massage_auto_stop_handle = None
        self._schedule_massage_resync("massage_auto_stop")

    def _schedule_massage_resync(self, reason: str) -> None:
        """Queue a single Stop when acknowledged massage state has been lost."""
        self._massage_resync_required = True
        self._massage_safety_state = "resynchronizing"
        self._cancel_massage_auto_stop()
        self._notify_listeners()
        if self._massage_resync_task is None or self._massage_resync_task.done():
            self._massage_resync_task = self.hass.async_create_task(
                self._async_resynchronize_massage(reason)
            )

    async def _async_resynchronize_massage(self, reason: str) -> None:
        """Attempt one acknowledged Stop after state loss; never retry Stop."""
        try:
            async with self._action_lock:
                await self._async_stop_massage(reason)
        except ControllerTimeoutError as err:
            _LOGGER.warning("Massage Stop was not confirmed during %s: %s", reason, err)
        finally:
            self._massage_resync_task = None

    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()
