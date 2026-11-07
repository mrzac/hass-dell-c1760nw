"""Constantes pour l'intégration Dell C1760nw."""
from datetime import timedelta
import logging

DOMAIN = "dell_c1760nw"
LOGGER = logging.getLogger(__package__)

DEFAULT_NAME = "Dell C1760nw"
DEFAULT_PORT = 161
DEFAULT_COMMUNITY = "public"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
FAST_SCAN_INTERVAL = timedelta(seconds=30)
SLOW_SCAN_INTERVAL = timedelta(seconds=300)

CONF_SNMP_COMMUNITY = "community"

# --- OIDs SNMP Standard (Printer MIB RFC 3805) ---
OID_PRINTER_STATUS = "1.3.6.1.2.1.25.3.5.1.1.1"
OID_PRINTER_DETECTED_ERROR = "1.3.6.1.2.1.25.3.5.1.2.1"
OID_SERIAL_NUMBER = "1.3.6.1.2.1.43.5.1.1.17.1"
OID_FIRMWARE_VERSION = "1.3.6.1.2.1.43.5.1.1.16.1"
OID_MAC_ADDRESS = "1.3.6.1.2.1.2.2.1.6.1"

# Compteurs de pages
OID_PAGE_COUNTER_TOTAL = "1.3.6.1.2.1.43.10.2.1.4.1.1"
OID_PAGE_COUNTER_COLOR = "1.3.6.1.2.1.43.10.2.1.4.1.2"
OID_PAGE_COUNTER_MONO = "1.3.6.1.2.1.43.10.2.1.4.1.3"

# Consommables
OID_SUPPLIES_DESC = "1.3.6.1.2.1.43.11.1.1.6"
OID_SUPPLIES_MAX_CAP = "1.3.6.1.2.1.43.11.1.1.8"
OID_SUPPLIES_LEVEL = "1.3.6.1.2.1.43.11.1.1.9"
