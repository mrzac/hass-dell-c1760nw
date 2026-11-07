"""Data coordinator for the Dell C1760nw."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import fetch_data
from .const import DOMAIN
from .snmp import SnmpError

_LOGGER = logging.getLogger(__name__)


class DellC1760nwCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, host: str, community: str, port: int, interval: int) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=interval))
        self.host = host
        self.community = community
        self.port = port

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await fetch_data(self.host, self.community, self.port)
        except SnmpError as err:
            raise UpdateFailed(f"SNMP error: {err}") from err
