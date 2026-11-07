"""Tests unitaires des valeurs Printer-MIB."""
from custom_components.dell_c1760nw.api.parser import (
    decode_error_state,
    format_mac,
    parse_firmware,
    parse_toner_level,
    split_alert_text,
    to_text,
)


def test_percent_unit_is_clamped():
    assert parse_toner_level(73, None, 19) == 73
    assert parse_toner_level(140, None, 19) == 100


def test_raw_level_requires_positive_capacity():
    assert parse_toner_level(250, 500, 3) == 50
    assert parse_toner_level(250, 0, 3) is None


def test_real_c1760nw_values():
    # Valeurs lues sur l'imprimante : unité 7 (impressions), capacités 700/2000.
    assert parse_toner_level(105, 700, 7) == 15
    assert parse_toner_level(210, 700, 7) == 30
    assert parse_toner_level(800, 2000, 7) == 40


def test_negative_snmp_state_is_not_a_percentage():
    assert parse_toner_level(-1, 100, 3) is None
    assert parse_toner_level(-2, 100, 3) is None
    assert parse_toner_level(-3, 100, 3) is None


def test_textual_status_is_not_a_level():
    assert parse_toner_level("Replace soon", None, None) is None


def test_utf8_text_is_decoded_not_mojibake():
    raw = "Prêt à imprimer".encode("utf-8")
    assert to_text(raw) == "Prêt à imprimer"


def test_mac_and_firmware():
    assert format_mac(bytes.fromhex("080037E0AFF8")) == "08:00:37:e0:af:f8"
    assert format_mac("08-00-37-E0-AF-F8") == "08:00:37:e0:af:f8"
    assert (
        parse_firmware("Dell C1760nw Color Printer; Net 18.05, Controller 1, Engine 05.09.00")
        == "Net 18.05, Controller 1, Engine 05.09.00"
    )


def test_alert_text_splits_vendor_code():
    text, code = split_alert_text("Remplacer la cartouche de toner cyan bientôt.:093-425")
    assert text == "Remplacer la cartouche de toner cyan bientôt"
    assert code == "093-425"
    assert split_alert_text("Prêt/Veille") == ("Prêt/Veille", None)


def test_error_state_bits():
    assert decode_error_state(b"\x04\x00")["jammed"] is True
    assert decode_error_state(b"\x08\x00")["door_open"] is True
    assert decode_error_state(b"\x40\x00")["no_paper"] is True
    assert decode_error_state(b"\x00\x04")["input_tray_empty"] is True
    assert not any(decode_error_state(b"\x00\x00").values())
    assert not any(decode_error_state(None).values())
