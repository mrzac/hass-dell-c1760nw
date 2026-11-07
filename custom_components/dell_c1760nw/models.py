"""Modèles de données normalisées pour l'imprimante Dell C1760nw."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PrinterAlert:
    """Ligne de prtAlertTable (Printer-MIB)."""

    severity: int | None = None
    group: int | None = None
    group_index: int | None = None
    code: int | None = None
    text: str = ""
    vendor_code: str | None = None


@dataclass
class DellPrinterData:
    """État observé de l'imprimante ; les valeurs restent None si non mesurées."""

    status: str = "Inconnu"
    printer_alert: str = "Aucune"
    alert_code: str | None = None
    page_counter_total: int | None = None
    page_counter_mono: int | None = None
    page_counter_color: int | None = None
    toner_black: int | None = None
    toner_cyan: int | None = None
    toner_magenta: int | None = None
    toner_yellow: int | None = None
    toner_status_black: str | None = None
    toner_status_cyan: str | None = None
    toner_status_magenta: str | None = None
    toner_status_yellow: str | None = None
    waste_toner_full: bool = False
    paper_tray_empty: bool = False
    paper_jam: bool = False
    cover_open: bool = False
    firmware_version: str | None = None
    mac_address: str | None = None
    serial_number: str | None = None
    ip_address: str = ""
