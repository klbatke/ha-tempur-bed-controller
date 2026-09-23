"""Last-requested lift-action sensors.

The controller protocol has no validated position readback.  These sensors are
therefore intentionally command history, rather than claimed bed position.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BedCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[BedCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up transparent lift command-history sensors."""
    async_add_entities(
        [
            *(TempurLiftActionSensor(entry.runtime_data, zone) for zone in ("head", "leg")),
            TempurMassageSafetySensor(entry.runtime_data),
        ]
    )


class TempurLiftActionSensor(SensorEntity):
    """Last acknowledged lift action for one zone; never physical position."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bed"

    def __init__(self, coordinator: BedCoordinator, zone: str) -> None:
        self.coordinator = coordinator
        self.zone = zone
        self._attr_unique_id = f"{coordinator.entry_id}_{zone}_last_requested_lift_action"
        self._attr_name = f"Last Requested {zone.title()} Lift Action"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> str | None:
        return self.coordinator.last_lift_actions[self.zone]

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {
            "state_meaning": "last_requested; physical lift position is not read from the controller"
        }


class TempurMassageSafetySensor(SensorEntity):
    """Report the integration's acknowledged massage safety state."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:shield-check"

    def __init__(self, coordinator: BedCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry_id}_massage_safety_state"
        self._attr_name = "Massage Safety State"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> str:
        return self.coordinator.massage_safety_state

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {
            "state_meaning": "integration safety state; controller massage state is not read back"
        }
