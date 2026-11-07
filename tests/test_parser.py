"""Tests unitaires des valeurs Printer-MIB."""
from custom_components.dell_c1760nw.api.parser import parse_toner_level


def test_percent_unit_is_clamped():
    assert parse_toner_level(73, None, 19) == 73
    assert parse_toner_level(140, None, 19) == 100


def test_raw_level_requires_positive_capacity():
    assert parse_toner_level(250, 500, 3) == 50
    assert parse_toner_level(250, 0, 3) is None


def test_negative_snmp_state_is_not_a_percentage():
    assert parse_toner_level(-1, 100, 3) is None
    assert parse_toner_level(-2, 100, 3) is None
    assert parse_toner_level(-3, 100, 3) is None


def test_textual_status_is_not_a_level():
    assert parse_toner_level("Replace soon", None, None) is None
