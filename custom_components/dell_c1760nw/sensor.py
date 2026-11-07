"""Entités capteurs pour la Dell C1760nw compatibles avec la carte Marlboro62/printers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import DellConfigEntry
from .entity import DellPrinterEntity
from .models import DellPrinterData


@dataclass(frozen=True, kw_only=True)
class DellSensorEntityDescription(SensorEntityDescription):
    """Description étendue avec fonction d'extraction de valeur."""

    value_fn: Callable[[DellPrinterData], str | int | None]


SENSOR_DESCRIPTIONS: tuple[DellSensorEntityDescription, ...] = (
    # --- Statut & Alertes ---
    DellSensorEntityDescription(
        key="status",
        name="Statut",
        icon="mdi:printer",
        value_fn=lambda d: d.status,
    ),
    DellSensorEntityDescription(
        key="printer_alert",
        name="Alerte actuelle",
        icon="mdi:alert-circle-outline",
        value_fn=lambda d: d.printer_alert,
    ),
    DellSensorEntityDescription(
        key="alert_code",
        name="Code d'erreur",
        icon="mdi:numeric",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.alert_code,
    ),
    # --- Toners (Nommés de manière standard pour la détection Marlboro62/printers) ---
    DellSensorEntityDescription(
        key="toner_black",
        name="Toner Noir",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:printer-3d-nozzle",
        value_fn=lambda d: d.toner_black,
    ),
    DellSensorEntityDescription(
        key="toner_cyan",
        name="Toner Cyan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:printer-3d-nozzle",
        value_fn=lambda d: d.toner_cyan,
    ),
    DellSensorEntityDescription(
        key="toner_magenta",
        name="Toner Magenta",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:printer-3d-nozzle",
        value_fn=lambda d: d.toner_magenta,
    ),
    DellSensorEntityDescription(
        key="toner_yellow",
        name="Toner Jaune",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:printer-3d-nozzle",
        value_fn=lambda d: d.toner_yellow,
    ),
    # --- États textuels des consommables (distincts des mesures en %) ---
    DellSensorEntityDescription(
        key="toner_status_black", name="État toner noir",
        entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:information-outline",
        value_fn=lambda d: d.toner_status_black,
    ),
    DellSensorEntityDescription(
        key="toner_status_cyan", name="État toner cyan",
        entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:information-outline",
        value_fn=lambda d: d.toner_status_cyan,
    ),
    DellSensorEntityDescription(
        key="toner_status_magenta", name="État toner magenta",
        entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:information-outline",
        value_fn=lambda d: d.toner_status_magenta,
    ),
    DellSensorEntityDescription(
        key="toner_status_yellow", name="État toner jaune",
        entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:information-outline",
        value_fn=lambda d: d.toner_status_yellow,
    ),
    # --- Compteurs de Pages ---
    DellSensorEntityDescription(
        key="page_counter_total",
        name="Compteur de pages total",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.page_counter_total,
    ),
    DellSensorEntityDescription(
        key="page_counter_mono",
        name="Pages Noir & Blanc",
        icon="mdi:file-document-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.page_counter_mono,
    ),
    DellSensorEntityDescription(
        key="page_counter_color",
        name="Pages Couleur",
        icon="mdi:file-image-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.page_counter_color,
    ),
    # --- Informations Système ---
    DellSensorEntityDescription(
        key="serial_number",
        name="Numéro de série",
        icon="mdi:barcode-scan",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.serial_number,
    ),
    DellSensorEntityDescription(
        key="firmware_version",
        name="Version Firmware",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.firmware_version,
    ),
    DellSensorEntityDescription(
        key="ip_address",
        name="Adresse IP",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.ip_address,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DellConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Instancie les entités capteurs."""
    coordinator = entry.runtime_data
    async_add_entities(
        DellPrinterSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class DellPrinterSensor(DellPrinterEntity, SensorEntity):
    """Représentation d'un capteur Dell C1760nw."""

    entity_description: DellSensorEntityDescription

    def __init__(self, coordinator, entry, description) -> None:
        """Initialisation de l'entité."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | int | None:
        """Récupère la valeur actualisée."""
        return self.entity_description.value_fn(self.coordinator.data)
