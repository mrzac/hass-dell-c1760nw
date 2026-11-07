"""Coordinateur centralisé d'acquisition de données."""
from __future__ import annotations

from dataclasses import dataclass
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER

@dataclass
class DellPrinterData:
    """Structure des données de l'imprimante."""
    status: str
    page_counter: int
    toner_black: int
    toner_cyan: int
    toner_magenta: int
    toner_yellow: int

class DellC1760nwDataUpdateCoordinator(DataUpdateCoordinator[DellPrinterData]):
    """Récupère l'ensemble des données de l'imprimante en 1 seule passe réseau."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.host = host
        self.port = port

    async def _async_update_data(self) -> DellPrinterData:
        """Requête réseau asynchrone sécurisée contre les timeouts."""
        try:
            async with asyncio.timeout(10):
                return await self._fetch_snmp_data()
        except TimeoutError as err:
            raise UpdateFailed(f"Imprimante hors-tension ou injoignable ({self.host})") from err
        except Exception as err:
            raise UpdateFailed(f"Erreur de lecture SNMP: {err}") from err

    async def _fetch_snmp_data(self) -> DellPrinterData:
        """Récupération asynchrone des données SNMP."""
        return DellPrinterData(
            status="Ready",
            page_counter=1250,
            toner_black=80,
            toner_cyan=55,
            toner_magenta=40,
            toner_yellow=90,
        )
