"""Lecture et extraction prudente des informations EWS Dell."""
from __future__ import annotations

import re

from ..models import DellPrinterData

COLORS = {
    "cyan": ("toner_cyan", "toner_status_cyan"),
    "magenta": ("toner_magenta", "toner_status_magenta"),
    "jaune": ("toner_yellow", "toner_status_yellow"),
    "yellow": ("toner_yellow", "toner_status_yellow"),
    "noir": ("toner_black", "toner_status_black"),
    "black": ("toner_black", "toner_status_black"),
}


def parse_ews_html(html: str, data: DellPrinterData) -> None:
    """Complète les données depuis EWS sans convertir un état textuel en pourcentage."""
    clean = re.sub(r"\s+", " ", html)
    for color, (level_attr, status_attr) in COLORS.items():
        pattern = rf"cartouche\s+{color}\s+niveau\s*:\s*(\d{{1,3}})\s*%"
        match = re.search(pattern, clean, re.IGNORECASE)
        if match and getattr(data, level_attr) is None:
            value = int(match.group(1))
            if 0 <= value <= 100:
                setattr(data, level_attr, value)

        text_pattern = rf"cartouche\s+{color}\s+niveau\s*:\s*([^<,;]+)"
        text_match = re.search(text_pattern, clean, re.IGNORECASE)
        if text_match:
            text = text_match.group(1).strip().rstrip(".")
            if text and not re.fullmatch(r"\d{1,3}\s*%", text):
                setattr(data, status_attr, text)

    alert = re.search(
        r"remplacer la cartouche de toner ([a-zàâäéèêëîïôöùûüç]+) bientôt\.?\s*:\s*(\d{3}-\d{3})",
        clean, re.IGNORECASE,
    )
    if alert:
        data.printer_alert = f"Remplacer cartouche {alert.group(1)} bientôt"
        data.alert_code = alert.group(2)

    counter = re.search(r"(?:compteur de pages|total page count)\s*:\s*(\d+)", clean, re.IGNORECASE)
    if counter and data.page_counter_total is None:
        data.page_counter_total = int(counter.group(1))

    lowered = clean.lower()
    if "bourrage" in lowered or "paper jam" in lowered:
        data.paper_jam = True
        data.printer_alert = "Bourrage papier"
    if "capot ouvert" in lowered or "porte ouverte" in lowered or "cover open" in lowered:
        data.cover_open = True
        data.printer_alert = "Capot ouvert"
