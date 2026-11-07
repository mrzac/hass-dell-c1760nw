"""Shared entity base."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DellC1760nwCoordinator


class DellEntity(CoordinatorEntity[DellC1760nwCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: DellC1760nwCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        fw = (coordinator.data or {}).get("firmware")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Dell C1760nw",
            manufacturer="Dell",
            model="C1760nw",
            serial_number=(coordinator.data or {}).get("serial"),
            sw_version=f"Net {fw['net']} / Engine {fw['engine']}" if fw else None,
            configuration_url=f"http://{coordinator.host}",
        )
