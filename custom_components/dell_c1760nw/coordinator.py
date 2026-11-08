"""Coordinateur de collecte résilient pour Dell C1760nw."""
from __future__ import annotations

import asyncio

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.ews import parse_ews_html
from .api.snmp import DellSnmpClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER
from .models import DellPrinterData

UPDATE_TIMEOUT = 20
EWS_TIMEOUT = 4


class DellC1760nwDataUpdateCoordinator(DataUpdateCoordinator[DellPrinterData]):
    """Interroge SNMP ; l'EWS ne sert que de secours si SNMP ne répond pas."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: DellSnmpClient,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    @property
    def host(self) -> str:
        """Adresse de l'imprimante."""
        return self.client.host

    async def _async_update_data(self) -> DellPrinterData:
        """Retourne une nouvelle photographie des données ou signale l'indisponibilité."""
        try:
            async with asyncio.timeout(UPDATE_TIMEOUT):
                data = await self.client.async_fetch()
                if data is not None:
                    return data

                LOGGER.debug("Pas de réponse SNMP de %s, essai EWS", self.host)
                fallback = DellPrinterData(ip_address=self.host)
                if await self._fetch_http_ews(fallback):
                    return fallback
                raise UpdateFailed(f"Aucune réponse SNMP ou EWS de {self.host}")
        except UpdateFailed:
            raise
        except (TimeoutError, aiohttp.ClientError, OSError) as err:
            raise UpdateFailed(f"Imprimante {self.host} inaccessible : {err}") from err
        except Exception as err:
            LOGGER.exception("Erreur inattendue lors de la lecture de %s", self.host)
            raise UpdateFailed(f"Erreur de lecture de l'imprimante : {err}") from err

    async def _fetch_http_ews(self, data: DellPrinterData) -> bool:
        """Lit la page EWS ; True si des informations ont été reconnues."""
        session = async_get_clientsession(self.hass)
        url = f"http://{self.host}/status/status.htm"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=EWS_TIMEOUT)
            ) as response:
                if response.status != 200:
                    return False
                return parse_ews_html(await response.text(), data)
        except (TimeoutError, aiohttp.ClientError, OSError):
            LOGGER.debug("EWS indisponible sur %s", self.host)
            return False


type DellConfigEntry = ConfigEntry[DellC1760nwDataUpdateCoordinator]
