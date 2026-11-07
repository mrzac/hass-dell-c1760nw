"""Entités boutons pour Dell C1760nw."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DellC1760nwDataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Instancie le bouton d'action."""
    coordinator: DellC1760nwDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DellPrinterRefreshButton(coordinator, entry)])

class DellPrinterRefreshButton(CoordinatorEntity[DellC1760nwDataUpdateCoordinator], ButtonEntity):
    """Bouton permettant de forcer l'actualisation des niveaux."""

    def __init__(
        self,
        coordinator: DellC1760nwDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_refresh_button"
        self._attr_name = "Rafraîchir l'état"
        self._attr_icon = "mdi:refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Dell C1760nw",
            manufacturer="Dell",
            model="C1760nw Color Laser Printer",
        )

    async def async_press(self) -> None:
        """Déclenche la mise à jour immédiate."""
        await self.coordinator.async_request_refresh()
