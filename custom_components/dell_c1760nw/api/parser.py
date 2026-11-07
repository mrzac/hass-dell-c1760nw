"""Normalisation des valeurs SNMP de la Dell C1760nw.

Fonctions pures (sans Home Assistant ni pysnmp) : testables telles quelles.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from ..models import DellPrinterData, PrinterAlert
from . import oids

PRINTER_STATUS = {
    1: "Autre",
    2: "Inconnu",
    3: "Prêt",
    4: "Impression",
    5: "Préchauffage",
}

# Mots de la description d'un consommable -> couleur du champ du modèle.
TONER_COLORS = {
    "black": "black",
    "noir": "black",
    "cyan": "cyan",
    "magenta": "magenta",
    "yellow": "yellow",
    "jaune": "yellow",
}
COLORS = ("black", "cyan", "magenta", "yellow")
TONER_SUPPLY_TYPES = {3, 21}  # toner, tonerCartridge

# prtAlertSeverityLevel : 3 = critique, 4 = avertissement (1 = information).
ACTIVE_SEVERITIES = (3, 4)
# prtAlertGroup
GROUP_INPUT = 8
GROUP_MARKER_SUPPLIES = 11
# prtAlertCode (RFC 3805). Confirmés sur le terrain : 23 (veille) et 1104.
CODE_COVER_OPEN = {3, 5}  # coverOpen, interlockOpen
CODE_JAM = {8}
CODE_SUBUNIT_EMPTY = {13}
CODE_TONER_LOW = {1101, 1104, 1115}  # vide, presque vide, cartouche absente
CODE_WASTE_TONER = {1107, 1109}  # bac récupérateur presque plein / plein

_VENDOR_CODE_RE = re.compile(
    r"^(?P<text>.*?)[\s.:]*(?P<code>\d{3}-\d{3})\s*$", re.DOTALL
)
_MAC_RE = re.compile(r"^(?:[0-9a-fA-F]{2}[-:]){5}[0-9a-fA-F]{2}$")


# --------------------------------------------------------------------------- #
# Conversions de base
# --------------------------------------------------------------------------- #
def to_int(value: Any) -> int | None:
    """Convertit en entier, ou None si impossible."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_octets(value: Any) -> bytes | None:
    """Octets bruts d'une valeur (bytes, str ou OctetString pysnmp)."""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    for name in ("asOctets", "as_octets"):
        func = getattr(value, name, None)
        if callable(func):
            try:
                return bytes(func())
            except Exception:  # noqa: BLE001 - valeur exotique, on abandonne
                return None
    if isinstance(value, str):
        return value.encode("utf-8")
    return None


def to_text(value: Any) -> str | None:
    """Décode une chaîne SNMP. L'imprimante envoie de l'UTF-8 (ex. « bientôt »)."""
    raw = to_octets(value)
    if raw is None:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    text = text.replace("\x00", "").strip()
    return text or None


def format_mac(value: Any) -> str | None:
    """Retourne une adresse MAC `aa:bb:cc:dd:ee:ff`."""
    raw = to_octets(value)
    if raw is None:
        return None
    if len(raw) == 6:
        return ":".join(f"{byte:02x}" for byte in raw)
    text = to_text(raw)
    if text and _MAC_RE.match(text):
        return text.replace("-", ":").lower()
    return None


def parse_firmware(sys_descr: str | None) -> str | None:
    """`Dell C1760nw Color Printer; Net 18.05, Controller …` -> `Net 18.05, …`."""
    if not sys_descr:
        return None
    if ";" in sys_descr:
        return sys_descr.split(";", 1)[1].strip() or None
    return sys_descr


def parse_toner_level(
    level_raw: object, max_capacity_raw: object = None, unit_raw: object = None
) -> int | None:
    """Retourne un pourcentage uniquement si les données SNMP permettent de le calculer.

    Printer-MIB : l'unité 19 est un pourcentage. Pour les autres unités (la C1760nw
    utilise 7 = impressions), une capacité maximale positive est nécessaire.
    Les valeurs négatives (-1/-2/-3) sont des états spéciaux, pas un niveau.
    """
    level = to_int(level_raw)
    if level is None or level < 0:
        return None

    if to_int(unit_raw) == 19:
        return max(0, min(100, level))

    maximum = to_int(max_capacity_raw)
    if maximum is None or maximum <= 0:
        return None
    return max(0, min(100, round(level * 100 / maximum)))


def toner_state_text(level_raw: object) -> str | None:
    """Texte des niveaux spéciaux Printer-MIB (valeurs négatives)."""
    return {-1: "Autre", -2: "Inconnu", -3: "Reste du toner"}.get(to_int(level_raw))


def decode_error_state(raw: bytes | None) -> dict[str, bool]:
    """Décode hrPrinterDetectedErrorState (BITS : le bit 0 est le bit de poids fort)."""
    first = raw[0] if raw and len(raw) > 0 else 0
    second = raw[1] if raw and len(raw) > 1 else 0
    return {
        "low_paper": bool(first & 0x80),
        "no_paper": bool(first & 0x40),
        "low_toner": bool(first & 0x20),
        "no_toner": bool(first & 0x10),
        "door_open": bool(first & 0x08),
        "jammed": bool(first & 0x04),
        "offline": bool(first & 0x02),
        "service_requested": bool(first & 0x01),
        "input_tray_missing": bool(second & 0x80),
        "input_tray_empty": bool(second & 0x04),
    }


def split_alert_text(text: str) -> tuple[str, str | None]:
    """`Remplacer … bientôt.:093-425` -> (`Remplacer … bientôt`, `093-425`)."""
    match = _VENDOR_CODE_RE.match(text)
    if match:
        return match.group("text").strip(), match.group("code")
    return text.strip(), None


def parse_alert(row: Mapping[str, Any]) -> PrinterAlert:
    """Construit une alerte depuis une ligne de prtAlertTable."""
    text, vendor_code = split_alert_text(to_text(row.get("description")) or "")
    return PrinterAlert(
        severity=to_int(row.get("severity")),
        group=to_int(row.get("group")),
        group_index=to_int(row.get("group_index")),
        code=to_int(row.get("code")),
        text=text,
        vendor_code=vendor_code,
    )


def _row_sort_key(key: str) -> tuple[int, ...]:
    return tuple(int(part) if part.isdigit() else 0 for part in key.split("."))


def _non_negative(value: int | None) -> int | None:
    return value if value is not None and value >= 0 else None


# --------------------------------------------------------------------------- #
# Assemblage
# --------------------------------------------------------------------------- #
def build_printer_data(
    host: str,
    scalars: Mapping[str, Any],
    supplies: Mapping[str, Mapping[str, Any]],
    alerts: Mapping[str, Mapping[str, Any]],
    counters: Mapping[str, Mapping[str, Any]],
) -> DellPrinterData:
    """Assemble un DellPrinterData à partir des valeurs SNMP brutes."""
    data = DellPrinterData(ip_address=host)

    data.status = PRINTER_STATUS.get(
        to_int(scalars.get(oids.HR_PRINTER_STATUS)), "Inconnu"
    )
    data.serial_number = to_text(scalars.get(oids.PRT_SERIAL))
    data.firmware_version = parse_firmware(to_text(scalars.get(oids.SYS_DESCR)))
    data.mac_address = format_mac(scalars.get(oids.IF_PHYS_ADDRESS))
    data.page_counter_total = _non_negative(to_int(scalars.get(oids.PRT_LIFE_COUNT)))

    # Bits d'erreur standard (source primaire pour bourrage / capot / papier).
    flags = decode_error_state(to_octets(scalars.get(oids.HR_PRINTER_ERROR_STATE)))
    data.paper_jam = flags["jammed"]
    data.cover_open = flags["door_open"]
    data.paper_tray_empty = flags["no_paper"] or flags["input_tray_empty"]

    # Consommables : découverts par description, jamais par index fixe.
    supply_colors: dict[str, str] = {}
    for key in sorted(supplies, key=_row_sort_key):
        row = supplies[key]
        supply_type = to_int(row.get("type"))
        if supply_type is not None and supply_type not in TONER_SUPPLY_TYPES:
            continue
        description = (to_text(row.get("description")) or "").lower()
        color = next(
            (c for token, c in TONER_COLORS.items() if token in description), None
        )
        if color is None:
            continue
        supply_colors[key.rsplit(".", 1)[-1]] = color
        level = parse_toner_level(
            row.get("level"), row.get("maximum"), row.get("unit")
        )
        setattr(data, f"toner_{color}", level)
        if level is None:
            setattr(data, f"toner_status_{color}", toner_state_text(row.get("level")))

    # Alertes : seules les alertes critiques/avertissements sont « actives ».
    parsed = [parse_alert(alerts[key]) for key in sorted(alerts, key=_row_sort_key)]
    active = sorted(
        (a for a in parsed if a.severity in ACTIVE_SEVERITIES),
        key=lambda a: a.severity or 99,
    )
    if active:
        data.printer_alert = active[0].text or "Alerte"
        data.alert_code = active[0].vendor_code
    for alert in active:
        if alert.code in CODE_JAM:
            data.paper_jam = True
        elif alert.code in CODE_COVER_OPEN:
            data.cover_open = True
        elif alert.code in CODE_SUBUNIT_EMPTY and alert.group == GROUP_INPUT:
            data.paper_tray_empty = True
        elif alert.code in CODE_WASTE_TONER:
            data.waste_toner_full = True
        elif alert.group == GROUP_MARKER_SUPPLIES and alert.code in CODE_TONER_LOW:
            color = supply_colors.get(str(alert.group_index))
            if color and alert.text:
                setattr(data, f"toner_status_{color}", alert.text)

    # Pas d'alerte sur une cartouche mesurée : état « OK » (absence d'alerte).
    for color in COLORS:
        if (
            getattr(data, f"toner_status_{color}") is None
            and getattr(data, f"toner_{color}") is not None
        ):
            setattr(data, f"toner_status_{color}", "OK")

    # Compteurs propriétaires, identifiés par leur libellé.
    for row in counters.values():
        label = (to_text(row.get("description")) or "").lower()
        value = _non_negative(to_int(row.get("value")))
        if label == "black printed impressions":
            data.page_counter_mono = value
        elif label == "color printed impressions":
            data.page_counter_color = value
        elif label == "total impressions" and data.page_counter_total is None:
            data.page_counter_total = value

    return data
