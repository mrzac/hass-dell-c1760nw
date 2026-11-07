"""Lecture SNMP basée sur la découverte des lignes Printer-MIB."""
from __future__ import annotations

from typing import Any

from .parser import parse_toner_level
from ..models import DellPrinterData

PRINTER_STATUS_OID = "1.3.6.1.2.1.25.3.5.1.1.1.0"
SERIAL_OID = "1.3.6.1.2.1.43.5.1.1.17.1"
PAGE_COUNT_OID = "1.3.6.1.2.1.43.10.2.1.4.1.1"
SUPPLIES_ROOT = "1.3.6.1.2.1.43.11.1.1"
SUPPLY_COLUMNS = {
    5: "type",
    6: "description",
    7: "unit",
    8: "maximum",
    9: "level",
}
TONER_NAMES = {
    "black": "toner_black",
    "noir": "toner_black",
    "cyan": "toner_cyan",
    "magenta": "toner_magenta",
    "yellow": "toner_yellow",
    "jaune": "toner_yellow",
}


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def async_read_printer(hass: Any, host: str, port: int, community: str) -> DellPrinterData | None:
    """Interroge Printer-MIB et découvre les consommables par description, pas par index."""
    try:
        from pysnmp.hlapi.v3arch.asyncio import (
            CommunityData,
            ContextData,
            ObjectIdentity,
            ObjectType,
            SnmpEngine,
            UdpTransportTarget,
            bulk_walk_cmd,
            get_cmd,
        )
    except ImportError:
        # Compatibilité avec les distributions qui exposent encore l'ancien chemin.
        try:
            from pysnmp.hlapi.asyncio import (  # type: ignore[no-redef]
                CommunityData, ContextData, ObjectIdentity, ObjectType,
                SnmpEngine, UdpTransportTarget, bulk_walk_cmd, get_cmd,
            )
        except ImportError:
            return None

    engine = SnmpEngine()
    try:
        target = await UdpTransportTarget.create((host, port), timeout=2, retries=1)
        auth = CommunityData(community, mpModel=1)
        error, status, index, values = await get_cmd(
            engine, auth, target, ContextData(),
            ObjectType(ObjectIdentity(PRINTER_STATUS_OID)),
            ObjectType(ObjectIdentity(SERIAL_OID)),
            ObjectType(ObjectIdentity(PAGE_COUNT_OID)),
        )
        if error or status:
            return None

        data = DellPrinterData(ip_address=host)
        binds = {str(item[0]): item[1] for item in values}
        status_code = str(binds.get(PRINTER_STATUS_OID, ""))
        data.status = {
            "1": "Autre", "2": "Inconnu", "3": "Prêt",
            "4": "Impression", "5": "Préchauffage",
            "6": "En arrêt", "7": "En veille",
        }.get(status_code, "Inconnu")
        serial = binds.get(SERIAL_OID)
        if serial is not None:
            data.serial_number = str(serial)
        data.page_counter_total = _as_int(binds.get(PAGE_COUNT_OID))

        # La table est indexée par la clé complète de ligne : aucun index couleur fixe.
        rows: dict[str, dict[str, Any]] = {}
        async for err, err_status, err_index, table in bulk_walk_cmd(
            engine, auth, target, ContextData(), 0, 20,
            ObjectType(ObjectIdentity(SUPPLIES_ROOT)),
            lexicographicMode=False,
        ):
            if err or err_status:
                break
            if not table:
                break
            for row in table:
                oid, value = str(row[0]), row[1]
                if not oid.startswith(SUPPLIES_ROOT + "."):
                    continue
                suffix = oid[len(SUPPLIES_ROOT) + 1:].split(".")
                if len(suffix) < 2:
                    continue
                try:
                    column = int(suffix[0])
                except ValueError:
                    continue
                if column in SUPPLY_COLUMNS:
                    row_key = ".".join(suffix[1:])
                    rows.setdefault(row_key, {})[SUPPLY_COLUMNS[column]] = value
            if len(rows) > 128:
                break

        for row in rows.values():
            description = str(row.get("description", "")).strip().lower()
            if not description:
                continue
            target_attr = next((attr for token, attr in TONER_NAMES.items() if token in description), None)
            if target_attr is None:
                if "waste" in description or "usagé" in description or "usagé" in description:
                    data.waste_toner_status = description
                continue
            level = parse_toner_level(row.get("level"), row.get("maximum"), row.get("unit"))
            setattr(data, target_attr, level)

        return data
    finally:
        try:
            engine.close_dispatcher()
        except Exception:
            pass
