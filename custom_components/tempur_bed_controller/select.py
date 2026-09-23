"""Last-requested preset and massage-mode controls."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import UNKNOWN_OPTION
from .coordinator import BedCoordinator

MASSAGE_STOPPED_OPTION = "Stopped"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[BedCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up last-requested selection controls."""
    async_add_entities((TempurMemorySelect(entry.runtime_data), TempurModeSelect(entry.runtime_data)))


class _BaseSelect(SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: BedCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))


class TempurMemorySelect(_BaseSelect):
    """Select a memory position and show only the last requested one."""

    _attr_options = (UNKNOWN_OPTION, "1", "2", "3", "4")
    _attr_icon = "mdi:bed"

    def __init__(self, coordinator: BedCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry_id}_last_requested_memory_position"
        self._attr_name = "Last Requested Memory Position"

    @property
    def current_option(self) -> str:
        return self.coordinator.last_memory or UNKNOWN_OPTION

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {"state_meaning": "last_requested; preset activity is not read from the controller"}

    async def async_select_option(self, option: str) -> None:
        if option == UNKNOWN_OPTION:
            self.coordinator.last_memory = None
            self.async_write_ha_state()
            return
        await self.coordinator.async_press(option)
        self.async_write_ha_state()


class TempurModeSelect(_BaseSelect):
    """Select a massage mode and show only the last requested one."""

    _attr_options = (MASSAGE_STOPPED_OPTION, "1", "2", "3", "4")
    _attr_icon = "mdi:wave"

    def __init__(self, coordinator: BedCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry_id}_last_requested_massage_mode"
        self._attr_name = "Last Requested Massage Mode"

    @property
    def current_option(self) -> str:
        return self.coordinator.last_massage_mode or MASSAGE_STOPPED_OPTION

    @property
    def available(self) -> bool:
        """Block massage modes until an acknowledged Stop establishes zero."""
        return self.coordinator.massage_controls_available

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {"state_meaning": "last_requested; mode activity is not read from the controller"}

    async def async_select_option(self, option: str) -> None:
        if option == MASSAGE_STOPPED_OPTION:
            await self.coordinator.async_press("massage_stop")
            self.async_write_ha_state()
            return
        await self.coordinator.async_press(f"mode_{option}")
        self.async_write_ha_state()
