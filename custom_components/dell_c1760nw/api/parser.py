"""Fonctions de normalisation des valeurs reçues de l'imprimante."""
from __future__ import annotations


def parse_toner_level(level_raw: object, max_capacity_raw: object = None, unit_raw: object = None) -> int | None:
    """Retourne un pourcentage uniquement si les données SNMP permettent de le calculer.

    Printer-MIB: l'unité 7 représente un pourcentage. Pour les autres unités,
    une capacité maximale positive est nécessaire pour normaliser la mesure.
    Les valeurs négatives (-1/-2/-3) représentent des états spéciaux, pas un niveau.
    """
    try:
        level = int(level_raw)
    except (TypeError, ValueError):
        return None
    if level < 0:
        return None

    try:
        unit = int(unit_raw) if unit_raw is not None else None
    except (TypeError, ValueError):
        unit = None

    if unit == 19:
        return max(0, min(100, level))

    try:
        maximum = int(max_capacity_raw)
    except (TypeError, ValueError):
        return None

    if maximum <= 0:
        return None
    return max(0, min(100, round(level * 100 / maximum)))
