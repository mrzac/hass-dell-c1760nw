"""Entités capteurs (Sensors) pour la Dell C1760nw."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DellC1760nwDataUpdateCoordinator, DellPrinterData


@dataclass
class DellSensorEntityDescription(SensorEntityDescription):
    """Description étendue avec fonction d'extraction de valeur."""

    value_fn: Callable[[DellPrinterData], str | int | None] = lambda d: None


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
    # --- Toners ---
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
    # --- Tambour & Consommables ---
    DellSensorEntityDescription(
        key="drum_life",
        name="Tambour d'imagerie",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:rotate-right",
        value_fn=lambda d: d.drum_life,
    ),
    DellSensorEntityDescription(
        key="waste_toner_status",
        name="Bac de toner usagé",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:delete-restore",
        value_fn=lambda d: d.waste_toner_status,
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
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Instancie les entités capteurs."""
    coordinator: DellC1760nwDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        DellPrinterSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class DellPrinterSensor(
    CoordinatorEntity[DellC1760nwDataUpdateCoordinator], SensorEntity
):
    """Représentation d'un capteur Dell C1760nw."""

    entity_description: DellSensorEntityDescription

    def __init__(
        self,
        coordinator: DellC1760nwDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DellSensorEntityDescription,
    ) -> None:
        """Initialisation de l'entité."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Dell C1760nw",
            manufacturer="Dell",
            model="C1760nw Color Laser Printer",
            configuration_url=f"http://{coordinator.host}",
        )

    @property
    def native_value(self) -> str | int | None:
        """Récupère la valeur actualisée."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
