"""Entité de base partagée par toutes les plateformes."""
from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DellC1760nwDataUpdateCoordinator, DellConfigEntry


class DellPrinterEntity(CoordinatorEntity[DellC1760nwDataUpdateCoordinator]):
    """Entité rattachée à l'appareil imprimante."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DellC1760nwDataUpdateCoordinator,
        entry: DellConfigEntry,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        data = coordinator.data
        connections = (
            {(CONNECTION_NETWORK_MAC, data.mac_address)} if data.mac_address else set()
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            connections=connections,
            name="Dell C1760nw",
            manufacturer="Dell",
            model="C1760nw Color Printer",
            serial_number=data.serial_number,
            sw_version=data.firmware_version,
            configuration_url=f"http://{coordinator.host}",
        )
