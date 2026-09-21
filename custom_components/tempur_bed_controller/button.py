"""Button entities for Tempur Bed Controller."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BedCoordinator


@dataclass(frozen=True, kw_only=True)
class TempurButtonDescription:
    key: str
    name: str
    icon: str


BUTTONS = (
    TempurButtonDescription(key="head_up", name="Head Up", icon="mdi:angle-acute"),
    TempurButtonDescription(key="head_down", name="Head Down", icon="mdi:angle-obtuse"),
    TempurButtonDescription(key="leg_up", name="Leg Up", icon="mdi:angle-acute"),
    TempurButtonDescription(key="leg_down", name="Leg Down", icon="mdi:angle-obtuse"),
    TempurButtonDescription(key="flat", name="Flat", icon="mdi:bed-flat"),
    *(TempurButtonDescription(key=value, name=f"Memory Position {value}", icon="mdi:numeric") for value in ("1", "2", "3", "4")),
    *(TempurButtonDescription(key=f"massage_{zone}_{direction}", name=f"{zone.title()} Massage {direction.title()}", icon="mdi:plus-minus") for zone in ("head", "lumbar", "leg") for direction in ("more", "less")),
    *(TempurButtonDescription(key=f"mode_{value}", name=f"Massage Mode {value}", icon="mdi:wave") for value in ("1", "2", "3", "4")),
    TempurButtonDescription(key="massage_stop", name="Massage Stop", icon="mdi:stop-circle"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[BedCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    async_add_entities(TempurButton(entry.runtime_data, description) for description in BUTTONS)


class TempurButton(ButtonEntity):
    """One explicit physical controller action."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BedCoordinator, description: TempurButtonDescription) -> None:
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry_id}_{description.key}"
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        await self.coordinator.async_press(self.entity_description.key)
