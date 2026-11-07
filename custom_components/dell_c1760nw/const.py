"""Constantes pour l'intégration Dell C1760nw."""
from datetime import timedelta
import logging

DOMAIN = "dell_c1760nw"
LOGGER = logging.getLogger(__package__)

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
DEFAULT_PORT = 161

# OIDs SNMP standards (Printer MIB - RFC 3805 / Dell C1760nw)
OID_PRINTER_STATUS = "1.3.6.1.2.1.25.3.5.1.1.1"
OID_PAGE_COUNTER = "1.3.6.1.2.1.43.10.2.1.4.1.1"
OID_TONER_BLACK = "1.3.6.1.2.1.43.11.1.1.9.1.1"
OID_TONER_CYAN = "1.3.6.1.2.1.43.11.1.1.9.1.2"
OID_TONER_MAGENTA = "1.3.6.1.2.1.43.11.1.1.9.1.3"
OID_TONER_YELLOW = "1.3.6.1.2.1.43.11.1.1.9.1.4"
