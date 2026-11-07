"""Sensors for the Dell C1760nw."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COLOR_LABELS, DOMAIN, NO_ALERT, SUPPLY_INDEXES
from .entity import DellEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [TonerSensor(c, entry, col) for col in SUPPLY_INDEXES.values()]
    entities += [
        PageSensor(c, entry, "page_count", "Compteur de pages", "page_count"),
        PageSensor(c, entry, "pages_black", "Pages noir", "pages_black"),
        PageSensor(c, entry, "pages_color", "Pages couleur", "pages_color"),
        StatusSensor(c, entry),
        AlertSensor(c, entry),
    ]
    async_add_entities(entities)


class TonerSensor(DellEntity, SensorEntity):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water"

    def __init__(self, coordinator, entry, color: str) -> None:
        super().__init__(coordinator, entry, f"toner_{color}")
        self._color = color
        self._attr_name = f"Toner {COLOR_LABELS[color].lower()}"

    @property
    def native_value(self):
        return self.coordinator.data["toners"].get(self._color, {}).get("percent")

    @property
    def extra_state_attributes(self):
        t = self.coordinator.data["toners"].get(self._color, {})
        return {
            "pages_restantes": t.get("pages_left"),
            "capacite_pages": t.get("capacity"),
            "description": t.get("description"),
        }


class PageSensor(DellEntity, SensorEntity):
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "pages"

    def __init__(self, coordinator, entry, key: str, name: str, data_key: str) -> None:
        super().__init__(coordinator, entry, key)
        self._attr_name = name
        self._data_key = data_key

    @property
    def native_value(self):
        return self.coordinator.data.get(self._data_key)


class StatusSensor(DellEntity, SensorEntity):
    _attr_name = "État"
    _attr_icon = "mdi:printer"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "status")

    @property
    def native_value(self):
        return self.coordinator.data["status"]

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data
        return {"message_afficheur": d["display"], "description_systeme": d["sys_descr"]}


class AlertSensor(DellEntity, SensorEntity):
    _attr_name = "Alerte"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "alert")

    @property
    def native_value(self):
        alerts = self.coordinator.data["alerts"]
        return alerts[0]["message"][:255] if alerts else NO_ALERT

    @property
    def extra_state_attributes(self):
        alerts = self.coordinator.data["alerts"]
        return {
            "nombre": len(alerts),
            "code": alerts[0]["code"] if alerts else None,
            "gravite": alerts[0]["severity"] if alerts else None,
            "alertes": alerts,
        }
