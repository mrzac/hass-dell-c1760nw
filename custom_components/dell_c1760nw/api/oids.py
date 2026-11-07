"""OID SNMP utilisés, validés sur un snmpwalk réel d'une C1760nw (firmware Net 18.05)."""
from __future__ import annotations

# --- Scalaires (GET) ---
SYS_DESCR = "1.3.6.1.2.1.1.1.0"
IF_PHYS_ADDRESS = "1.3.6.1.2.1.2.2.1.6.1"
# hrPrinterStatus.<hrDeviceIndex> : l'index 1 est celui de l'imprimante.
HR_PRINTER_STATUS = "1.3.6.1.2.1.25.3.5.1.1.1"
HR_PRINTER_ERROR_STATE = "1.3.6.1.2.1.25.3.5.1.2.1"
PRT_SERIAL = "1.3.6.1.2.1.43.5.1.1.17.1"
PRT_LIFE_COUNT = "1.3.6.1.2.1.43.10.2.1.4.1.1"

SCALAR_OIDS: tuple[str, ...] = (
    SYS_DESCR,
    IF_PHYS_ADDRESS,
    HR_PRINTER_STATUS,
    HR_PRINTER_ERROR_STATE,
    PRT_SERIAL,
    PRT_LIFE_COUNT,
)
IDENTITY_OIDS: tuple[str, ...] = (SYS_DESCR, PRT_SERIAL)

# --- Tables (walk) : colonne SNMP -> nom de champ ---
SUPPLIES_ROOT = "1.3.6.1.2.1.43.11.1.1"  # prtMarkerSuppliesTable
SUPPLY_COLUMNS = {5: "type", 6: "description", 7: "unit", 8: "maximum", 9: "level"}

ALERT_ROOT = "1.3.6.1.2.1.43.18.1.1"  # prtAlertTable
ALERT_COLUMNS = {
    2: "severity",
    4: "group",
    5: "group_index",
    7: "code",
    8: "description",
}

# Compteurs d'impressions propriétaires (Fuji Xerox / Dell), décrits par texte.
COUNTER_ROOT = "1.3.6.1.4.1.253.8.53.13.2.1"
COUNTER_COLUMNS = {6: "value", 8: "description"}
