"""Coordinateur centralisé d'acquisition de données SNMP pour Dell C1760nw."""
from __future__ import annotations

from dataclasses import dataclass
import asyncio

from pysnmp.hlapi.asyncio import (
    getCmd,
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER

# OIDs SNMP standards (Printer MIB RFC 3805 & Xerox/Dell MIB)
OID_STATUS = "1.3.6.1.2.1.25.3.5.1.1.1"

# Compteurs de pages
OID_PAGE_TOTAL = "1.3.6.1.2.1.43.10.2.1.4.1.1"
OID_PAGE_COLOR = "1.3.6.1.4.1.253.8.53.13.2.1.6.1.20.33"

# Niveaux actuels (Level)
OID_TONER_BLACK_LEVEL = "1.3.6.1.2.1.43.11.1.1.9.1.1"
OID_TONER_CYAN_LEVEL = "1.3.6.1.2.1.43.11.1.1.9.1.2"
OID_TONER_MAGENTA_LEVEL = "1.3.6.1.2.1.43.11.1.1.9.1.3"
OID_TONER_YELLOW_LEVEL = "1.3.6.1.2.1.43.11.1.1.9.1.4"

# Capacités maximales (Max Capacity)
OID_TONER_BLACK_MAX = "1.3.6.1.2.1.43.11.1.1.8.1.1"
OID_TONER_CYAN_MAX = "1.3.6.1.2.1.43.11.1.1.8.1.2"
OID_TONER_MAGENTA_MAX = "1.3.6.1.2.1.43.11.1.1.8.1.3"
OID_TONER_YELLOW_MAX = "1.3.6.1.2.1.43.11.1.1.8.1.4"

# Diagnostic & Matériel
OID_TRAY_STATUS = "1.3.6.1.2.1.43.8.2.1.10.1.1"
OID_SERIAL_NUMBER = "1.3.6.1.2.1.43.5.1.1.17.1"


@dataclass
class DellPrinterData:
    """Structure des données réelles de l'imprimante."""

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
    """Récupère l'ensemble des données SNMP en une seule passe réseau."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialise le coordinateur SNMP."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.host = host
        self.port = port
        self.snmp_engine = SnmpEngine()

    async def _async_update_data(self) -> DellPrinterData:
        """Requête réseau SNMP asynchrone sécurisée contre les timeouts."""
        try:
            async with asyncio.timeout(10):
                return await self._fetch_snmp_data()
        except TimeoutError as err:
            raise UpdateFailed(
                f"Imprimante hors-tension ou injoignable ({self.host})"
            ) from err
        except Exception as err:
            raise UpdateFailed(f"Erreur de lecture SNMP: {err}") from err

    async def _fetch_snmp_oid(self, oid: str) -> int | str | None:
        """Exécute une requête SNMP GET asynchrone sur un OID spécifique."""
        try:
            error_indication, error_status, error_index, var_binds = await getCmd(
                self.snmp_engine,
                CommunityData("public", mpModel=0),
                UdpTransportTarget((self.host, self.port), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
            )
            if error_indication or error_status:
                LOGGER.debug("Erreur SNMP OID %s: %s", oid, error_indication or error_status)
                return None

            for _, val in var_binds:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return str(val)
        except Exception as err:
            LOGGER.debug("Exception SNMP OID %s: %s", oid, err)
            return None

    def _calculate_percentage(self, level: int | None, max_capacity: int | None) -> int:
        """Calcule le pourcentage réel (0-100%) à partir des valeurs brutes SNMP."""
        if level is None or level < 0:
            return 0
        if max_capacity is None or max_capacity <= 0 or max_capacity == 100:
            return min(100, max(0, level))
        return min(100, max(0, int((level / max_capacity) * 100)))

    async def _fetch_snmp_data(self) -> DellPrinterData:
        """Exécute les requêtes SNMP en parallèle et traite les résultats."""
        raw_results = await asyncio.gather(
            self._fetch_snmp_oid(OID_STATUS),
            self._fetch_snmp_oid(OID_PAGE_TOTAL),
            self._fetch_snmp_oid(OID_PAGE_COLOR),
            self._fetch_snmp_oid(OID_TONER_BLACK_LEVEL),
            self._fetch_snmp_oid(OID_TONER_BLACK_MAX),
            self._fetch_snmp_oid(OID_TONER_CYAN_LEVEL),
            self._fetch_snmp_oid(OID_TONER_CYAN_MAX),
            self._fetch_snmp_oid(OID_TONER_MAGENTA_LEVEL),
            self._fetch_snmp_oid(OID_TONER_MAGENTA_MAX),
            self._fetch_snmp_oid(OID_TONER_YELLOW_LEVEL),
            self._fetch_snmp_oid(OID_TONER_YELLOW_MAX),
            self._fetch_snmp_oid(OID_TRAY_STATUS),
            self._fetch_snmp_oid(OID_SERIAL_NUMBER),
        )

        (
            status_raw,
            total_pages_raw,
            color_pages_raw,
            k_level, k_max,
            c_level, c_max,
            m_level, m_max,
            y_level, y_max,
            tray_raw,
            sn_raw,
        ) = raw_results

        # Traitement des compteurs de pages
        total_pages = int(total_pages_raw) if isinstance(total_pages_raw, int) else 0
        color_pages = int(color_pages_raw) if isinstance(color_pages_raw, int) else 0
        mono_pages = max(0, total_pages - color_pages)

        # Calcul des pourcentages réels de toner
        toner_k = self._calculate_percentage(
            k_level if isinstance(k_level, int) else None,
            k_max if isinstance(k_max, int) else None,
        )
        toner_c = self._calculate_percentage(
            c_level if isinstance(c_level, int) else None,
            c_max if isinstance(c_max, int) else None,
        )
        toner_m = self._calculate_percentage(
            m_level if isinstance(m_level, int) else None,
            m_max if isinstance(m_max, int) else None,
        )
        toner_y = self._calculate_percentage(
            y_level if isinstance(y_level, int) else None,
            y_max if isinstance(y_max, int) else None,
        )

        # Formatage des données de statut
        status_str = "Prête" if status_raw in (3, "3", "Ready") else "Prête / En attente"
        tray_str = "OK" if tray_raw in (0, "0", "OK") else "Vérifier le bac"
        serial = str(sn_raw) if sn_raw else None

        return DellPrinterData(
            status=status_str,
            page_counter_total=total_pages,
            page_counter_mono=mono_pages,
            page_counter_color=color_pages,
            toner_black=toner_k,
            toner_cyan=toner_c,
            toner_magenta=toner_m,
            toner_yellow=toner_y,
            paper_tray_status=tray_str,
            serial_number=serial,
        )