"""Binary sensors for the Dell C1760nw."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DellEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([RearCoverSensor(hass.data[DOMAIN][entry.entry_id], entry)])


class RearCoverSensor(DellEntity, BinarySensorEntity):
    _attr_name = "Capot arrière"
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "rear_cover")

    @property
    def is_on(self):
        return self.coordinator.data["cover_open"]
