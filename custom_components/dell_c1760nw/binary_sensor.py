"""Entités capteurs binaires pour la Dell C1760nw."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import DellConfigEntry
from .entity import DellPrinterEntity
from .models import DellPrinterData


@dataclass(frozen=True, kw_only=True)
class DellBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Description personnalisée pour les entités binaires."""

    is_on_fn: Callable[[DellPrinterData], bool]


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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DellConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Instancie les capteurs binaires."""
    coordinator = entry.runtime_data
    async_add_entities(
        DellPrinterBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class DellPrinterBinarySensor(DellPrinterEntity, BinarySensorEntity):
    """Capteur binaire Dell C1760nw."""

    entity_description: DellBinarySensorEntityDescription

    def __init__(self, coordinator, entry, description) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Détermine l'état du capteur binaire."""
        return self.entity_description.is_on_fn(self.coordinator.data)
