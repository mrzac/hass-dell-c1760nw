"""Lecture de l'état de la Dell C1760nw en SNMP v2c (Printer-MIB + compteurs Dell)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..models import DellPrinterData
from . import oids
from .ber import SnmpError
from .parser import build_printer_data, to_text
from .transport import DEFAULT_RETRIES, DEFAULT_TIMEOUT, SnmpClient

_LOGGER = logging.getLogger(__name__)


@dataclass
class PrinterIdentity:
    """Informations d'identification lues pendant la configuration."""

    serial: str | None
    description: str | None


class DellSnmpClient:
    """Interroge l'imprimante ; aucune dépendance externe (BER/UDP intégrés)."""

    def __init__(
        self,
        host: str,
        port: int,
        community: str,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self.host = host
        self.port = port
        self.community = community
        self._client = SnmpClient(host, port, community, timeout, retries)

    async def _async_get(self, oid_list: tuple[str, ...]) -> dict[str, Any] | None:
        """GET ; None si l'imprimante ne répond pas ou n'a aucune valeur utile."""
        try:
            values = await self._client.get(oid_list)
        except (SnmpError, OSError) as err:
            _LOGGER.debug("SNMP GET %s : %s", self.host, err)
            return None
        if all(value is None for value in values.values()):
            _LOGGER.debug("SNMP GET %s : aucune valeur exploitable", self.host)
            return None
        return values

    async def _async_walk_rows(
        self, root: str, columns: dict[int, str]
    ) -> dict[str, dict[str, Any]]:
        """Parcourt une table ; clé = suffixe de ligne, colonnes nommées."""
        try:
            entries = await self._client.walk(root)
        except (SnmpError, OSError) as err:
            _LOGGER.debug("SNMP walk %s (%s) : %s", root, self.host, err)
            return {}
        prefix = root + "."
        rows: dict[str, dict[str, Any]] = {}
        for oid, value in entries:
            parts = oid[len(prefix):].split(".")
            if len(parts) < 2 or not parts[0].isdigit():
                continue
            column = columns.get(int(parts[0]))
            if column is not None:
                rows.setdefault(".".join(parts[1:]), {})[column] = value
        return rows

    async def async_identify(self) -> PrinterIdentity | None:
        """Vérifie que l'hôte répond en SNMP et lit série + description."""
        values = await self._async_get(oids.IDENTITY_OIDS)
        if values is None:
            return None
        return PrinterIdentity(
            serial=to_text(values.get(oids.PRT_SERIAL)),
            description=to_text(values.get(oids.SYS_DESCR)),
        )

    async def async_fetch(self) -> DellPrinterData | None:
        """Lit l'état complet ; None si l'imprimante ne répond pas en SNMP."""
        scalars = await self._async_get(oids.SCALAR_OIDS)
        if scalars is None:
            return None
        supplies = await self._async_walk_rows(oids.SUPPLIES_ROOT, oids.SUPPLY_COLUMNS)
        alerts = await self._async_walk_rows(oids.ALERT_ROOT, oids.ALERT_COLUMNS)
        counters = await self._async_walk_rows(oids.COUNTER_ROOT, oids.COUNTER_COLUMNS)
        return build_printer_data(self.host, scalars, supplies, alerts, counters)
