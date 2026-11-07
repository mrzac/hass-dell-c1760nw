"""Bouton de rafraîchissement pour Dell C1760nw."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import DellConfigEntry
from .entity import DellPrinterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DellConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Instancie le bouton de contrôle réellement pris en charge."""
    async_add_entities([DellPrinterRefreshButton(entry.runtime_data, entry)])


class DellPrinterRefreshButton(DellPrinterEntity, ButtonEntity):
    """Bouton pour forcer le rafraîchissement immédiat."""

    _attr_name = "Rafraîchir l'état"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "refresh_button")

    async def async_press(self) -> None:
        """Déclenche l'actualisation."""
        await self.coordinator.async_request_refresh()
