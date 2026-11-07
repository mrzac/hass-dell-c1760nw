"""Client SNMP asynchrone pour la Dell C1760nw (Printer-MIB + compteurs Dell)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterator

from ..models import DellPrinterData
from . import oids
from .parser import build_printer_data, to_text

_LOGGER = logging.getLogger(__name__)

SNMP_TIMEOUT = 2
SNMP_RETRIES = 1
BULK_REPETITIONS = 20
MAX_ROWS = 256
_MISSING_TYPES = {"NoSuchInstance", "NoSuchObject", "EndOfMibView"}


@dataclass
class PrinterIdentity:
    """Informations d'identification lues pendant la configuration."""

    serial: str | None
    description: str | None


def load_pysnmp() -> SimpleNamespace:
    """Importe pysnmp (à appeler dans un executor : l'import est bloquant)."""
    from pysnmp.hlapi.v3arch.asyncio import (  # noqa: PLC0415
        CommunityData,
        ContextData,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        bulk_walk_cmd,
        get_cmd,
    )

    return SimpleNamespace(
        CommunityData=CommunityData,
        ContextData=ContextData,
        ObjectIdentity=ObjectIdentity,
        ObjectType=ObjectType,
        SnmpEngine=SnmpEngine,
        UdpTransportTarget=UdpTransportTarget,
        bulk_walk_cmd=bulk_walk_cmd,
        get_cmd=get_cmd,
    )


def oid_text(identity: Any) -> str:
    """OID pointé numérique, sans point initial."""
    for name in ("get_oid", "getOid"):
        func = getattr(identity, name, None)
        if callable(func):
            try:
                return str(func()).lstrip(".")
            except Exception:  # noqa: BLE001 - identité non résolue
                break
    return str(identity).lstrip(".")


def clean_value(value: Any) -> Any:
    """Remplace les valeurs « absentes » SNMP (noSuchInstance…) par None."""
    if value is not None and value.__class__.__name__ in _MISSING_TYPES:
        return None
    return value


def iter_varbinds(binds: Any) -> Iterator[tuple[Any, Any]]:
    """Itère sur des (nom, valeur), que la réponse soit plate ou imbriquée."""
    for item in binds or ():
        try:
            first = item[0]
        except (TypeError, IndexError, KeyError):
            continue
        if isinstance(first, (list, tuple)):  # ligne imbriquée : on descend
            yield from iter_varbinds(item)
            continue
        try:
            yield first, item[1]
        except (TypeError, IndexError, KeyError):
            continue


class DellSnmpClient:
    """Interroge l'imprimante en SNMP v2c ; le moteur pysnmp est réutilisé."""

    def __init__(self, host: str, port: int, community: str) -> None:
        self.host = host
        self.port = port
        self.community = community
        self._lib: SimpleNamespace | None = None
        self._engine: Any = None

    async def async_setup(self, hass: Any) -> None:
        """Charge pysnmp et crée le moteur hors de la boucle d'événements."""
        if self._engine is not None:
            return
        self._lib = await hass.async_add_executor_job(load_pysnmp)
        self._engine = await hass.async_add_executor_job(self._lib.SnmpEngine)

    def close(self) -> None:
        """Libère le moteur SNMP."""
        engine, self._engine = self._engine, None
        if engine is not None:
            try:
                engine.close_dispatcher()
            except Exception:  # noqa: BLE001 - arrêt best-effort
                _LOGGER.debug("Fermeture du moteur SNMP impossible", exc_info=True)

    async def _async_context(self) -> tuple[Any, Any]:
        assert self._lib is not None  # noqa: S101 - async_setup() obligatoire
        target = await self._lib.UdpTransportTarget.create(
            (self.host, self.port), timeout=SNMP_TIMEOUT, retries=SNMP_RETRIES
        )
        auth = self._lib.CommunityData(self.community, mpModel=1)
        return target, auth

    async def _async_get(
        self, target: Any, auth: Any, oid_list: tuple[str, ...]
    ) -> dict[str, Any] | None:
        lib = self._lib
        assert lib is not None  # noqa: S101
        error, status, index, binds = await lib.get_cmd(
            self._engine,
            auth,
            target,
            lib.ContextData(),
            *(lib.ObjectType(lib.ObjectIdentity(oid)) for oid in oid_list),
        )
        if error:
            _LOGGER.debug("SNMP GET %s : %s", self.host, error)
            return None
        if status:
            _LOGGER.debug("SNMP GET %s : erreur %s (index %s)", self.host, status, index)
            return None
        values = {
            oid_text(name): clean_value(value) for name, value in iter_varbinds(binds)
        }
        if all(value is None for value in values.values()):
            _LOGGER.debug("SNMP GET %s : aucune valeur exploitable", self.host)
            return None
        return values

    async def _async_walk_rows(
        self, target: Any, auth: Any, root: str, columns: dict[int, str]
    ) -> dict[str, dict[str, Any]]:
        """Parcourt une table ; clé = suffixe de ligne, colonnes nommées."""
        lib = self._lib
        assert lib is not None  # noqa: S101
        prefix = root + "."
        rows: dict[str, dict[str, Any]] = {}
        async for error, status, _index, binds in lib.bulk_walk_cmd(
            self._engine,
            auth,
            target,
            lib.ContextData(),
            0,
            BULK_REPETITIONS,
            lib.ObjectType(lib.ObjectIdentity(root)),
            lexicographicMode=False,
        ):
            if error or status:
                _LOGGER.debug("SNMP walk %s (%s) : %s", root, self.host, error or status)
                break
            for name, value in iter_varbinds(binds):
                oid = oid_text(name)
                if not oid.startswith(prefix):
                    continue
                parts = oid[len(prefix):].split(".")
                if len(parts) < 2 or not parts[0].isdigit():
                    continue
                column = columns.get(int(parts[0]))
                if column is not None:
                    row = rows.setdefault(".".join(parts[1:]), {})
                    row[column] = clean_value(value)
            if len(rows) > MAX_ROWS:
                break
        return rows

    async def async_identify(self) -> PrinterIdentity | None:
        """Vérifie que l'hôte répond en SNMP et lit série + description."""
        target, auth = await self._async_context()
        values = await self._async_get(target, auth, oids.IDENTITY_OIDS)
        if values is None:
            return None
        return PrinterIdentity(
            serial=to_text(values.get(oids.PRT_SERIAL)),
            description=to_text(values.get(oids.SYS_DESCR)),
        )

    async def async_fetch(self) -> DellPrinterData | None:
        """Lit l'état complet ; None si l'imprimante ne répond pas en SNMP."""
        target, auth = await self._async_context()
        scalars = await self._async_get(target, auth, oids.SCALAR_OIDS)
        if scalars is None:
            return None
        supplies = await self._async_walk_rows(
            target, auth, oids.SUPPLIES_ROOT, oids.SUPPLY_COLUMNS
        )
        alerts = await self._async_walk_rows(
            target, auth, oids.ALERT_ROOT, oids.ALERT_COLUMNS
        )
        counters = await self._async_walk_rows(
            target, auth, oids.COUNTER_ROOT, oids.COUNTER_COLUMNS
        )
        return build_printer_data(self.host, scalars, supplies, alerts, counters)
