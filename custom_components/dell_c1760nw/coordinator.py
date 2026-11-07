"""Coordinateur de collecte résilient pour Dell C1760nw."""
from __future__ import annotations

import asyncio
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.ews import parse_ews_html
from .api.snmp import async_read_printer
from .const import (
    CONF_SNMP_COMMUNITY, DEFAULT_COMMUNITY, DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER,
)
from .models import DellPrinterData

# Compatibilité avec les imports historiques déjà utilisés par d'autres plateformes.
__all__ = ["DellPrinterData", "DellC1760nwDataUpdateCoordinator", "parse_toner_level", "parse_status_text_to_level"]


def parse_toner_level(level_raw: object, max_cap_raw: object = None) -> int | None:
    """Normalise une mesure réelle ; les valeurs d'état SNMP négatives restent inconnues."""
    from .api.parser import parse_toner_level as _parse
    return _parse(level_raw, max_cap_raw)


def parse_status_text_to_level(status_text: str) -> None:
    """Les états textuels ne constituent pas une mesure de niveau."""
    return None


class DellC1760nwDataUpdateCoordinator(DataUpdateCoordinator[DellPrinterData]):
    """Interroge SNMP puis EWS sans dégrader les dernières données valides."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int = DEFAULT_PORT,
        community: str = DEFAULT_COMMUNITY,
    ) -> None:
        super().__init__(
            hass, LOGGER, name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL
        )
        self.host = host
        self.port = port
        self.community = community

    async def _async_update_data(self) -> DellPrinterData:
        """Retourne une nouvelle photographie des données ou signale l'indisponibilité."""
        try:
            async with asyncio.timeout(12):
                data = await async_read_printer(
                    self.hass, self.host, self.port, self.community
                )
                if data is None:
                    data = DellPrinterData(ip_address=self.host)

                ews_ok = await self._fetch_http_ews(data)
                if data.status == "Inconnu" and not ews_ok:
                    raise UpdateFailed(f"Aucune réponse SNMP ou EWS de {self.host}")

                return data
        except UpdateFailed:
            raise
        except (TimeoutError, aiohttp.ClientError, OSError) as err:
            raise UpdateFailed(f"Imprimante {self.host} inaccessible: {err}") from err
        except Exception as err:
            LOGGER.exception("Erreur inattendue lors de la lecture de %s", self.host)
            raise UpdateFailed(f"Erreur de lecture de l'imprimante: {err}") from err

    async def _fetch_http_ews(self, data: DellPrinterData) -> bool:
        """Récupère les informations complémentaires depuis la page EWS."""
        session = async_get_clientsession(self.hass)
        url = f"http://{self.host}/status/status.htm"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=4)) as response:
                if response.status != 200:
                    return False
                parse_ews_html(await response.text(), data)
                return True
        except (TimeoutError, aiohttp.ClientError, OSError):
            LOGGER.debug("EWS indisponible sur %s", self.host)
            return False
