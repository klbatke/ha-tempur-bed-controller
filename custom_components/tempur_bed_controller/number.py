"""Requested massage-intensity number entities."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BedCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[BedCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up requested-intensity controls."""
    async_add_entities(TempurMassageIntensity(entry.runtime_data, zone) for zone in ("head", "lumbar", "leg"))


class TempurMassageIntensity(NumberEntity):
    """Exact requested massage intensity, not physical state feedback."""

    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = "box"

    def __init__(self, coordinator: BedCoordinator, zone: str) -> None:
        self.coordinator = coordinator
        self.zone = zone
        self._attr_unique_id = f"{coordinator.entry_id}_massage_{zone}_requested_intensity"
        self._attr_name = f"{zone.title()} Massage Requested Intensity"
        self._attr_icon = "mdi:vibrate"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> int | None:
        return self.coordinator.massage_levels[self.zone]

    @property
    def available(self) -> bool:
        """Avoid exposing an unknown level while Stop is unconfirmed."""
        return self.coordinator.massage_controls_available

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {"state_meaning": "last_requested; physical state is not read from the controller"}

    async def async_set_native_value(self, value: float) -> None:
        if not float(value).is_integer():
            raise ValueError("Massage intensity must be a whole number")
        await self.coordinator.async_set_massage_level(self.zone, int(value))
        self.async_write_ha_state()
