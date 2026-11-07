"""Lecture de secours de la page EWS Dell (utilisée uniquement si SNMP ne répond pas)."""
from __future__ import annotations

import re
from html.parser import HTMLParser

from ..models import DellPrinterData

COLORS = {
    "cyan": ("toner_cyan", "toner_status_cyan"),
    "magenta": ("toner_magenta", "toner_status_magenta"),
    "jaune": ("toner_yellow", "toner_status_yellow"),
    "yellow": ("toner_yellow", "toner_status_yellow"),
    "noir": ("toner_black", "toner_status_black"),
    "black": ("toner_black", "toner_status_black"),
}


class _TextExtractor(HTMLParser):
    """Extrait le texte visible ; les nœuds sont séparés par « | »."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def html_to_text(html: str) -> str:
    """Texte visible d'une page HTML, nœuds séparés par « | »."""
    extractor = _TextExtractor()
    extractor.feed(html)
    extractor.close()
    return " | ".join(extractor.parts)


def parse_ews_html(html: str, data: DellPrinterData) -> bool:
    """Complète `data` depuis l'EWS sans convertir un état textuel en pourcentage.

    Retourne True si au moins une information a été reconnue.
    """
    text = html_to_text(html)
    found = False

    for color, (level_attr, status_attr) in COLORS.items():
        label = rf"cartouche[\s|]+{color}[\s|]+niveau\s*:\s*"
        percent = re.search(label + r"(\d{1,3})\s*%", text, re.IGNORECASE)
        if percent and getattr(data, level_attr) is None:
            value = int(percent.group(1))
            if 0 <= value <= 100:
                setattr(data, level_attr, value)
                found = True

        textual = re.search(label + r"([^|]+)", text, re.IGNORECASE)
        if textual:
            state = textual.group(1).strip().rstrip(".")
            if state and not re.fullmatch(r"\d{1,3}\s*%", state):
                setattr(data, status_attr, state)
                found = True

    counter = re.search(
        r"(?:compteur de pages|total page count)[\s|]*:?[\s|]*(\d+)",
        text,
        re.IGNORECASE,
    )
    if counter and data.page_counter_total is None:
        data.page_counter_total = int(counter.group(1))
        found = True

    return found
