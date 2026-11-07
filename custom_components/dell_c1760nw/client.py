"""Fetch and interpret the printer's SNMP data (no Home Assistant dependency)."""
from __future__ import annotations

import logging
import re
from typing import Any

from .const import (
    OID_ALERT_DESC,
    OID_ALERT_SEVERITY,
    OID_COVER_STATUS,
    OID_DISPLAY,
    OID_PAGE_COUNT,
    OID_PAGES_BLACK,
    OID_PAGES_COLOR,
    OID_PRINTER_STATUS,
    OID_SERIAL,
    OID_SUPPLY_DESC,
    OID_SUPPLY_LEVEL,
    OID_SUPPLY_MAX,
    OID_SYS_DESCR,
    PRINTER_STATUS,
    SUPPLY_INDEXES,
)
from .snmp import SnmpError, snmp_get, snmp_walk

_LOGGER = logging.getLogger(__name__)

_FW_RE = re.compile(r"Net\s+([\w.]+).*?Controller\s+(\w+).*?Engine\s+([\w.]+)", re.I)
_CODE_RE = re.compile(r"^(.*?)\s*:\s*(\d{3}-\d{3})$")


def compute_percent(level: Any, capacity: Any) -> int | None:
    """Level/capacity in %, handling SNMP special values (-1, -2, -3)."""
    if not isinstance(level, int) or not isinstance(capacity, int):
        return None
    if level < 0 or capacity <= 0:
        return None
    return max(0, min(100, round(level * 100 / capacity)))


def color_from_desc(desc: str | None, default: str) -> str:
    d = (desc or "").lower()
    for word, color in (
        ("cyan", "cyan"),
        ("magenta", "magenta"),
        ("yellow", "yellow"),
        ("jaune", "yellow"),
        ("black", "black"),
        ("noir", "black"),
    ):
        if word in d:
            return color
    return default


def parse_firmware(sys_descr: str | None) -> dict[str, str] | None:
    m = _FW_RE.search(sys_descr or "")
    if not m:
        return None
    return {"net": m.group(1), "controller": m.group(2), "engine": m.group(3)}


def parse_alerts(severities: dict[str, Any], descs: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep critical (3) and warning (4) alerts; split off the Dell code."""
    alerts: list[dict[str, Any]] = []
    for oid, desc in descs.items():
        suffix = oid[len(OID_ALERT_DESC) + 1 :]
        sev = severities.get(f"{OID_ALERT_SEVERITY}.{suffix}")
        if sev not in (3, 4) or not desc:
            continue
        m = _CODE_RE.match(desc)
        message, code = (m.group(1), m.group(2)) if m else (desc, None)
        alerts.append(
            {
                "severity": "critical" if sev == 3 else "warning",
                "message": message.strip(),
                "code": code,
            }
        )
    alerts.sort(key=lambda a: a["severity"] != "critical")
    return alerts


def build_data(raw: dict[str, Any], alerts: list[dict[str, Any]]) -> dict[str, Any]:
    toners: dict[str, dict[str, Any]] = {}
    for i, default_color in SUPPLY_INDEXES.items():
        desc = raw.get(OID_SUPPLY_DESC + str(i))
        level = raw.get(OID_SUPPLY_LEVEL + str(i))
        cap = raw.get(OID_SUPPLY_MAX + str(i))
        toners[color_from_desc(desc, default_color)] = {
            "percent": compute_percent(level, cap),
            # The C1760nw reports levels in pages (impressions)
            "pages_left": level if isinstance(level, int) and level >= 0 else None,
            "capacity": cap if isinstance(cap, int) and cap > 0 else None,
            "description": desc,
        }
    status_code = raw.get(OID_PRINTER_STATUS)
    cover = raw.get(OID_COVER_STATUS)
    sys_descr = raw.get(OID_SYS_DESCR)
    return {
        "sys_descr": sys_descr,
        "firmware": parse_firmware(sys_descr),
        "serial": raw.get(OID_SERIAL) or None,
        "page_count": raw.get(OID_PAGE_COUNT),
        "pages_black": raw.get(OID_PAGES_BLACK),
        "pages_color": raw.get(OID_PAGES_COLOR),
        "status": PRINTER_STATUS.get(status_code, "Inconnu") if status_code is not None else None,
        "display": raw.get(OID_DISPLAY) or None,
        # prtCoverStatus: 3 doorOpen, 4 doorClosed, 5 interlockOpen, 6 interlockClosed
        "cover_open": None if cover is None else cover in (3, 5),
        "toners": toners,
        "alerts": alerts,
    }


async def fetch_data(host: str, community: str, port: int) -> dict[str, Any]:
    oids = [
        OID_SYS_DESCR,
        OID_SERIAL,
        OID_PAGE_COUNT,
        OID_PAGES_BLACK,
        OID_PAGES_COLOR,
        OID_PRINTER_STATUS,
        OID_DISPLAY,
        OID_COVER_STATUS,
    ]
    for i in SUPPLY_INDEXES:
        oids += [OID_SUPPLY_DESC + str(i), OID_SUPPLY_MAX + str(i), OID_SUPPLY_LEVEL + str(i)]
    raw = await snmp_get(host, oids, community, port)

    alerts: list[dict[str, Any]] = []
    try:
        sev = await snmp_walk(host, OID_ALERT_SEVERITY, community, port)
        desc = await snmp_walk(host, OID_ALERT_DESC, community, port)
        alerts = parse_alerts(sev, desc)
    except SnmpError as err:
        _LOGGER.debug("Could not read printer alerts: %s", err)
    return build_data(raw, alerts)
