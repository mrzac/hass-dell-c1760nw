"""Constants for the Dell C1760nw integration."""
from __future__ import annotations

DOMAIN = "dell_c1760nw"

CONF_COMMUNITY = "community"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_PORT = 161
DEFAULT_COMMUNITY = "public"
DEFAULT_SCAN_INTERVAL = 300  # seconds

# Standard MIBs (verified on a real C1760nw)
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SERIAL = "1.3.6.1.2.1.43.5.1.1.17.1"  # prtGeneralSerialNumber
OID_PAGE_COUNT = "1.3.6.1.2.1.43.10.2.1.4.1.1"  # prtMarkerLifeCount
OID_PRINTER_STATUS = "1.3.6.1.2.1.25.3.5.1.1.1"  # hrPrinterStatus
OID_DISPLAY = "1.3.6.1.2.1.43.16.5.1.2.1.1"  # prtConsoleDisplayBufferText
OID_COVER_STATUS = "1.3.6.1.2.1.43.6.1.1.3.1.1"  # prtCoverStatus (Rear Cover)
OID_SUPPLY_DESC = "1.3.6.1.2.1.43.11.1.1.6.1."  # + index
OID_SUPPLY_MAX = "1.3.6.1.2.1.43.11.1.1.8.1."  # + index (pages)
OID_SUPPLY_LEVEL = "1.3.6.1.2.1.43.11.1.1.9.1."  # + index (pages)
OID_ALERT_SEVERITY = "1.3.6.1.2.1.43.18.1.1.2"  # table, walked
OID_ALERT_DESC = "1.3.6.1.2.1.43.18.1.1.8"  # table, walked

# Dell/Xerox private counters
OID_PAGES_BLACK = "1.3.6.1.4.1.253.8.53.13.2.1.6.1.20.7"
OID_PAGES_COLOR = "1.3.6.1.4.1.253.8.53.13.2.1.6.1.20.29"

SUPPLY_INDEXES = {1: "cyan", 2: "magenta", 3: "yellow", 4: "black"}
COLOR_LABELS = {"cyan": "Cyan", "magenta": "Magenta", "yellow": "Jaune", "black": "Noir"}

PRINTER_STATUS = {1: "Autre", 2: "Inconnu", 3: "Prêt", 4: "Impression", 5: "Préchauffage"}
NO_ALERT = "Aucune"
