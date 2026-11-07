"""Entités capteurs binaires pour la Dell C1760nw."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DellC1760nwDataUpdateCoordinator, DellPrinterData


@dataclass
class DellBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Description personnalisée pour les entités binaires."""

    is_on_fn: Callable[[DellPrinterData], bool] = lambda d: False


BINARY_SENSOR_DESCRIPTIONS: tuple[DellBinarySensorEntityDescription, ...] = (
    DellBinarySensorEntityDescription(
        key="paper_jam",
        name="Bourrage papier",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda d: d.paper_jam,
    ),
    DellBinarySensorEntityDescription(
        key="cover_open",
        name="Capot ouvert",
        device_class=BinarySensorDeviceClass.DOOR,
        is_on_fn=lambda d: d.cover_open,
    ),
    DellBinarySensorEntityDescription(
        key="paper_tray_empty",
        name="Bac à papier vide",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda d: d.paper_tray_empty,
    ),
    DellBinarySensorEntityDescription(
        key="waste_toner_full",
        name="Bac récepteur toner plein",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda d: d.waste_toner_full,
    ),
    DellBinarySensorEntityDescription(
        key="non_dell_toner",
        name="Toner non officiel détecté",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda d: d.non_dell_toner,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Instancie les capteurs binaires."""
    coordinator: DellC1760nwDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        DellPrinterBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class DellPrinterBinarySensor(
    CoordinatorEntity[DellC1760nwDataUpdateCoordinator], BinarySensorEntity
):
    """Capteur binaire Dell C1760nw."""

    entity_description: DellBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: DellC1760nwDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DellBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Dell C1760nw",
            manufacturer="Dell",
            model="C1760nw Color Laser Printer",
        )

    @property
    def is_on(self) -> bool:
        """Détermine l'état du capteur binaire."""
        if self.coordinator.data is None:
            return False
        return self.entity_description.is_on_fn(self.coordinator.data)
