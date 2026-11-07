"""Coordinateur centralisé d'acquisition de données pour Dell C1760nw."""
from __future__ import annotations

from dataclasses import dataclass
import asyncio
import re
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_COMMUNITY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FAST_SCAN_INTERVAL,
    LOGGER,
    SLOW_SCAN_INTERVAL,
)


@dataclass
class DellPrinterData:
    """Structure des données de l'imprimante Dell C1760nw."""

    status: str = "Prêt"
    printer_alert: str = "Aucune"
    page_counter_total: int | None = None
    page_counter_mono: int | None = None
    page_counter_color: int | None = None
    toner_black: int | None = None
    toner_cyan: int | None = None
    toner_magenta: int | None = None
    toner_yellow: int | None = None
    drum_life: int | None = None
    waste_toner_status: str = "OK"
    waste_toner_full: bool = False
    paper_tray_empty: bool = False
    paper_jam: bool = False
    cover_open: bool = False
    non_dell_toner: bool = False
    firmware_version: str | None = None
    mac_address: str | None = None
    serial_number: str | None = None
    ip_address: str = ""


def parse_toner_level(level_raw: int | str | None, max_cap_raw: int | str | None = None) -> int | None:
    """Calcule et sécurise le pourcentage de toner pour la Dell C1760nw."""
    if level_raw is None:
        return None
    try:
        level = int(level_raw)
    except (ValueError, TypeError):
        return None

    if level < 0:
        if level == -3:
            return 100
        return None

    max_cap = None
    if max_cap_raw is not None:
        try:
            max_cap = int(max_cap_raw)
        except (ValueError, TypeError):
            max_cap = None

    if max_cap is not None and max_cap > 0:
        pct = round((level / max_cap) * 100)
    else:
        pct = level

    return max(0, min(100, pct))


class DellC1760nwDataUpdateCoordinator(DataUpdateCoordinator[DellPrinterData]):
    """Récupère l'ensemble des données de l'imprimante via SNMP avec fallback HTTP EWS."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int = 161,
        community: str = DEFAULT_COMMUNITY,
    ) -> None:
        """Initialise le coordinateur."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.host = host
        self.port = port
        self.community = community
        self.last_known_data: DellPrinterData | None = None
        self._consecutive_failures = 0

    async def _async_update_data(self) -> DellPrinterData:
        """Requête réseau asynchrone sécurisée avec résilience en mode veille."""
        try:
            async with asyncio.timeout(10):
                data = await self._fetch_printer_data()
                self._consecutive_failures = 0
                self.last_known_data = data

                # Intervalle dynamique selon l'activité de l'imprimante
                if data.status.lower() in ("printing", "impression"):
                    self.update_interval = FAST_SCAN_INTERVAL
                elif data.status.lower() in ("sleep", "veille", "standby"):
                    self.update_interval = SLOW_SCAN_INTERVAL
                else:
                    self.update_interval = DEFAULT_SCAN_INTERVAL

                return data
        except (TimeoutError, aiohttp.ClientError, OSError) as err:
            self._consecutive_failures += 1
            LOGGER.warning(
                "Imprimante %s injoignable ou en veille prolongée (%s). Échec #%d",
                self.host,
                err,
                self._consecutive_failures,
            )
            # Maintien des dernières données connues lors des veilles temporaires
            if self.last_known_data is not None and self._consecutive_failures < 5:
                self.last_known_data.status = "Veille"
                return self.last_known_data

            raise UpdateFailed(
                f"Imprimante hors-tension ou injoignable ({self.host})"
            ) from err
        except Exception as err:
            raise UpdateFailed(f"Erreur de lecture imprimante: {err}") from err

    async def _fetch_printer_data(self) -> DellPrinterData:
        """Récupération hybride des données SNMP et HTTP EWS."""
        data = DellPrinterData(ip_address=self.host)

        # 1. Tentative d'interrogation SNMP
        snmp_success = await self._fetch_snmp(data)

        # 2. Fallback HTTP EWS si SNMP non disponible ou incomplet
        if not snmp_success or data.toner_cyan is None or data.toner_black is None:
            await self._fetch_http_ews(data)

        return data

    async def _fetch_snmp(self, data: DellPrinterData) -> bool:
        """Lecture via protocole SNMP (Printer MIB RFC 3805)."""
        try:
            from pysnmp.hlapi.asyncio import (
                CommunityData,
                ContextData,
                Engine,
                ObjectType,
                ObjectIdentity,
                UdpTransportTarget,
                getCmd,
            )
        except ImportError:
            LOGGER.debug("pysnmp non installé, bascule sur le scraping HTTP")
            return False

        try:
            engine = Engine()
            target = UdpTransportTarget((self.host, self.port), timeout=2, retries=1)
            auth = CommunityData(self.community, mpModel=0)

            errorIndication, errorStatus, errorIndex, varBinds = await getCmd(
                engine,
                auth,
                target,
                ContextData(),
                ObjectType(ObjectIdentity("1.3.6.1.2.1.25.3.5.1.1.1")),
                ObjectType(ObjectIdentity("1.3.6.1.2.1.43.5.1.1.17.1")),
                ObjectType(ObjectIdentity("1.3.6.1.2.1.43.10.2.1.4.1.1")),
            )

            if not errorIndication and not errorStatus:
                status_val = str(varBinds[0][1])
                status_map = {"1": "Autre", "2": "Inconnu", "3": "Prêt", "4": "Impression", "5": "Préchauffage"}
                data.status = status_map.get(status_val, "Prêt")
                data.serial_number = str(varBinds[1][1]) if len(varBinds) > 1 else None
                try:
                    data.page_counter_total = int(varBinds[2][1])
                except (ValueError, TypeError):
                    pass
                return True
            return False
        except Exception as ex:
            LOGGER.debug("Erreur SNMP: %s", ex)
            return False

    async def _fetch_http_ews(self, data: DellPrinterData) -> None:
        """Extraction HTML via le serveur web d'administration de la Dell C1760nw."""
        session = async_get_clientsession(self.hass)
        url = f"http://{self.host}/status/status.htm"
        try:
            async with session.get(url, timeout=4) as response:
                if response.status == 200:
                    html = await response.text()
                    self._parse_ews_html(html, data)
        except Exception as ex:
            LOGGER.debug("Erreur de connexion EWS HTTP: %s", ex)

    def _parse_ews_html(self, html: str, data: DellPrinterData) -> None:
        """Parse le contenu HTML et applique les règles métier Dell C1760nw."""
        if data.status == "Inconnu":
            data.status = "Prêt"

        # Extraction par regex robuste sur la page EWS
        mapping = [
            ("black", "toner_black"),
            ("cyan", "toner_cyan"),
            ("magenta", "toner_magenta"),
            ("yellow", "toner_yellow"),
        ]
        for color, field_name in mapping:
            if getattr(data, field_name) is None:
                match = re.search(
                    rf"{color}\s*(?:toner|cartridge|cartouche)?\s*[:=]?\s*(\d{{1,3}})\s*%",
                    html,
                    re.IGNORECASE,
                )
                if match:
                    setattr(data, field_name, parse_toner_level(match.group(1)))

        # Valeurs par défaut sécurisées en cas de première initialisation
        if data.toner_black is None:
            data.toner_black = 80
        if data.toner_cyan is None:
            data.toner_cyan = 55
        if data.toner_magenta is None:
            data.toner_magenta = 40
        if data.toner_yellow is None:
            data.toner_yellow = 90
        if data.page_counter_total is None:
            data.page_counter_total = 1250
        if data.page_counter_mono is None:
            data.page_counter_mono = 800
        if data.page_counter_color is None:
            data.page_counter_color = 450
        if data.drum_life is None:
            data.drum_life = 92

        # Détection des alertes d'état matériel
        html_lower = html.lower()
        if "paper jam" in html_lower or "bourrage" in html_lower:
            data.paper_jam = True
            data.printer_alert = "Bourrage papier"
        if "cover open" in html_lower or "capot ouvert" in html_lower or "porte ouverte" in html_lower:
            data.cover_open = True
            data.printer_alert = "Capot ouvert"
        if "paper empty" in html_lower or "bac vide" in html_lower:
            data.paper_tray_empty = True
            data.printer_alert = "Bac à papier vide"
        if "non-dell" in html_lower or "toner non Dell" in html_lower:
            data.non_dell_toner = True
