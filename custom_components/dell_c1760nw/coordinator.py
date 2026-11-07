"""Coordinateur centralisé d'acquisition de données réelles pour Dell C1760nw."""
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
    """Structure des données réelles de l'imprimante Dell C1760nw."""

    status: str = "Prêt"
    printer_alert: str = "Aucune"
    alert_code: str | None = None
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


def parse_status_text_to_level(status_text: str) -> int | None:
    """Convertit les états textuels EWS Dell C1760nw (ex: 'Remplacer bientôt', 'OK') en pourcentage estimé."""
    txt = status_text.lower()
    if "remplacer bientôt" in txt or "replace soon" in txt:
        return 15
    elif "remplacer" in txt or "replace" in txt or "vide" in txt or "empty" in txt:
        return 0
    elif "ok" in txt or "normal" in txt:
        return 75
    return None


class DellC1760nwDataUpdateCoordinator(DataUpdateCoordinator[DellPrinterData]):
    """Récupère l'ensemble des données réelles via SNMP avec fallback HTTP EWS."""

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

        # 1. Tentative SNMP
        snmp_success = await self._fetch_snmp(data)

        # 2. Fallback / Complément HTTP EWS
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
            LOGGER.debug("pysnmp non installé, utilisation du scraping HTTP EWS")
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
        """Scrappe la page web /status/status.htm de la Dell C1760nw."""
        session = async_get_clientsession(self.hass)
        url = f"http://{self.host}/status/status.htm"
        try:
            async with session.get(url, timeout=4) as response:
                if response.status == 200:
                    html = await response.text()
                    self._parse_ews_html(html, data)
        except Exception as ex:
            LOGGER.debug("Erreur HTTP EWS: %s", ex)

    def _parse_ews_html(self, html: str, data: DellPrinterData) -> None:
        """Parse précisément le HTML de la page web Dell C1760nw (niveaux réels et messages de code d'erreur)."""
        html_clean = re.sub(r'\s+', ' ', html)

        # Parsing des cartouches depuis le texte HTML (ex: 'Cartouche cyan Niveau : Remplacer bientôt')
        colors_map = {
            'cyan': 'toner_cyan',
            'magenta': 'toner_magenta',
            'jaune': 'toner_yellow',
            'yellow': 'toner_yellow',
            'noir': 'toner_black',
            'black': 'toner_black',
        }

        for color_name, attr_name in colors_map.items():
            # Cherche motif '%', sinon motif textuel 'Niveau : XXX'
            pattern_pct = rf"cartouche\s+{color_name}\s+niveau\s*:\s*(\d{{1,3}})\s*%"
            match_pct = re.search(pattern_pct, html_clean, re.IGNORECASE)
            if match_pct:
                setattr(data, attr_name, int(match_pct.group(1)))
            else:
                pattern_txt = rf"cartouche\s+{color_name}\s+niveau\s*:\s*([a-zàâäéèêëîïôöùûüç\s]+)"
                match_txt = re.search(pattern_txt, html_clean, re.IGNORECASE)
                if match_txt:
                    status_str = match_txt.group(1).strip()
                    lvl = parse_status_text_to_level(status_str)
                    if lvl is not None:
                        setattr(data, attr_name, lvl)

        # Extraction des alertes spécifiques (ex: 'Remplacer la cartouche de toner cyan bientôt.:093-425')
        alert_match = re.search(r"remplacer la cartouche de toner ([a-z]+) bientôt\.?\s*:\s*(\d{3}-\d{3})", html_clean, re.IGNORECASE)
        if alert_match:
            color_alert = alert_match.group(1)
            code = alert_match.group(2)
            data.printer_alert = f"Remplacer cartouche {color_alert} bientôt"
            data.alert_code = code

        # Extraction du compteur de pages si présent dans EWS
        counter_match = re.search(r"(?:compteur de pages|total page count)\s*:\s*(\d+)", html_clean, re.IGNORECASE)
        if counter_match:
            data.page_counter_total = int(counter_match.group(1))

        # Statuts matériels
        if "bourrage" in html_clean.lower() or "paper jam" in html_clean.lower():
            data.paper_jam = True
            data.printer_alert = "Bourrage papier"
        if "capot ouvert" in html_clean.lower() or "porte ouverte" in html_clean.lower() or "cover open" in html_clean.lower():
            data.cover_open = True
            data.printer_alert = "Capot ouvert"
