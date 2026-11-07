"""Constantes pour l'intégration Dell C1760nw."""
from datetime import timedelta
import logging

DOMAIN = "dell_c1760nw"
LOGGER = logging.getLogger(__package__)

DEFAULT_NAME = "Dell C1760nw"
DEFAULT_PORT = 161
DEFAULT_COMMUNITY = "public"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

CONF_SNMP_COMMUNITY = "community"
