"""Initialisation et gestion du cycle de vie du composant Dell C1760nw."""
from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .api.snmp import DellSnmpClient
from .const import CONF_SNMP_COMMUNITY, DEFAULT_COMMUNITY, DEFAULT_PORT
from .coordinator import DellC1760nwDataUpdateCoordinator, DellConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: DellConfigEntry) -> bool:
    """Initialise une instance d'imprimante via ConfigEntry."""
    client = DellSnmpClient(
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
        entry.data.get(CONF_SNMP_COMMUNITY, DEFAULT_COMMUNITY),
    )
    coordinator = DellC1760nwDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DellConfigEntry) -> bool:
    """Décharge proprement les entités (le moteur SNMP est fermé via on_unload)."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
