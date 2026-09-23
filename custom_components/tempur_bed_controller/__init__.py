"""Tempur Bed Controller integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import BedCoordinator

type TempurConfigEntry = ConfigEntry[BedCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TempurConfigEntry) -> bool:
    """Set up Tempur Bed Controller from a config entry."""
    coordinator = BedCoordinator(
        hass, entry.data["host"], entry.data["port"], entry.title, entry.entry_id
    )
    await coordinator.async_setup()
    entry.runtime_data = coordinator
    await coordinator.async_initialize_massage_safety()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TempurConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_close()
    return unloaded
