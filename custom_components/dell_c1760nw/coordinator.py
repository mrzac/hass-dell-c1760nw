"""Coordinateur centralisé d'acquisition de données pour Dell C1760nw."""
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
    page_counter_total: int
    page_counter_mono: int
    page_counter_color: int
    toner_black: int
    toner_cyan: int
    toner_magenta: int
    toner_yellow: int
    paper_tray_status: str
    serial_number: str | None


class DellC1760nwDataUpdateCoordinator(DataUpdateCoordinator[DellPrinterData]):
    """Récupère l'ensemble des données de l'imprimante en 1 seule passe réseau."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialise le coordinateur."""
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
            raise UpdateFailed(
                f"Imprimante hors-tension ou injoignable ({self.host})"
            ) from err
        except Exception as err:
            raise UpdateFailed(f"Erreur de lecture SNMP: {err}") from err

    async def _fetch_snmp_data(self) -> DellPrinterData:
        """Récupération des données SNMP de l'imprimante."""
        # TODO: Remplacer les valeurs par les requêtes SNMP réelles via pysnmp-lextudio
        return DellPrinterData(
            status="Ready",
            page_counter_total=1250,
            page_counter_mono=800,
            page_counter_color=450,
            toner_black=80,
            toner_cyan=55,
            toner_magenta=40,
            toner_yellow=90,
            paper_tray_status="OK",
            serial_number="CN-0XXXXX",
        )