"""Test de régression construit sur le snmpwalk réel d'une C1760nw."""
from custom_components.dell_c1760nw.api import oids
from custom_components.dell_c1760nw.api.parser import build_printer_data

SCALARS = {
    oids.SYS_DESCR: "Dell C1760nw Color Printer; Net 18.05, Controller 201803071433, Engine 05.09.00",
    oids.IF_PHYS_ADDRESS: bytes.fromhex("080037E0AFF8"),
    oids.HR_PRINTER_STATUS: 3,  # idle
    oids.HR_PRINTER_ERROR_STATE: b"\x00\x00",
    oids.PRT_SERIAL: "ZHD016176",
    oids.PRT_LIFE_COUNT: 1251,
}
SUPPLIES = {
    "1.1": {"type": 3, "description": b"Cartouche cyan", "unit": 7, "maximum": 700, "level": 105},
    "1.2": {"type": 3, "description": b"Cartouche magenta", "unit": 7, "maximum": 700, "level": 210},
    "1.3": {"type": 3, "description": b"Cartouche jaune", "unit": 7, "maximum": 700, "level": 210},
    "1.4": {"type": 3, "description": b"Cartouche noir", "unit": 7, "maximum": 2000, "level": 800},
}
ALERTS = {
    "1.1": {
        "severity": 4,
        "group": 11,
        "group_index": 1,
        "code": 1104,
        "description": "Remplacer la cartouche de toner cyan bientôt.:093-425".encode("utf-8"),
    },
    "1.2": {
        "severity": 1,
        "group": 5,
        "group_index": -1,
        "code": 23,
        "description": "Prêt/Veille".encode("utf-8"),
    },
}
COUNTERS = {
    "1.20.1": {"value": 1251, "description": b"Total Impressions"},
    "1.20.7": {"value": 540, "description": b"Black Printed Impressions"},
    "1.20.29": {"value": 711, "description": b"Color Printed Impressions"},
    "1.20.33": {"value": 711, "description": b"Color Impressions"},
    "1.20.34": {"value": 540, "description": b"Black Impressions "},
}


def build(**overrides):
    args = {
        "scalars": SCALARS,
        "supplies": SUPPLIES,
        "alerts": ALERTS,
        "counters": COUNTERS,
    }
    args.update(overrides)
    return build_printer_data("192.168.50.47", **args)


def test_real_printer_snapshot():
    data = build()
    assert data.status == "Prêt"
    assert data.serial_number == "ZHD016176"
    assert data.mac_address == "08:00:37:e0:af:f8"
    assert data.firmware_version == "Net 18.05, Controller 201803071433, Engine 05.09.00"
    assert (data.toner_cyan, data.toner_magenta, data.toner_yellow, data.toner_black) == (
        15,
        30,
        30,
        40,
    )
    assert data.page_counter_total == 1251
    assert data.page_counter_mono == 540
    assert data.page_counter_color == 711


def test_active_alert_is_reported_and_power_saver_is_ignored():
    data = build()
    assert data.printer_alert == "Remplacer la cartouche de toner cyan bientôt"
    assert data.alert_code == "093-425"
    assert data.toner_status_cyan == "Remplacer la cartouche de toner cyan bientôt"
    assert data.toner_status_black == "OK"
    assert not (data.paper_jam or data.cover_open or data.paper_tray_empty)
    assert data.waste_toner_full is False


def test_no_alert_means_none():
    data = build(alerts={})
    assert data.printer_alert == "Aucune"
    assert data.alert_code is None


def test_error_state_sets_binary_flags():
    scalars = {**SCALARS, oids.HR_PRINTER_ERROR_STATE: b"\x4c\x00"}  # noPaper+door+jam
    data = build(scalars=scalars)
    assert data.paper_jam and data.cover_open and data.paper_tray_empty


def test_special_levels_are_not_percentages():
    supplies = {"1.1": {"type": 3, "description": b"Cartouche cyan", "unit": 7, "maximum": 700, "level": -3}}
    data = build(supplies=supplies, alerts={})
    assert data.toner_cyan is None
    assert data.toner_status_cyan == "Reste du toner"


def test_waste_container_is_not_a_color_cartridge():
    supplies = {"1.5": {"type": 4, "description": b"Bac usage", "unit": 19, "maximum": 100, "level": 50}}
    data = build(supplies=supplies)
    assert data.toner_black is None
