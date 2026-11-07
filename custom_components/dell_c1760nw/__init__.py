"""Initialisation et gestion du cycle de vie du composant Dell C1760nw."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SNMP_COMMUNITY, DEFAULT_COMMUNITY, DEFAULT_PORT, DOMAIN
from .coordinator import DellC1760nwDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialise une instance d'imprimante via ConfigEntry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    community = entry.data.get(CONF_SNMP_COMMUNITY, DEFAULT_COMMUNITY)

    coordinator = DellC1760nwDataUpdateCoordinator(
        hass, host=host, port=port, community=community
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge proprement les entités lors de la suppression/désactivation."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
