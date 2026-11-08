"""Transport UDP et client Dell, testés contre un faux agent SNMP local."""
import asyncio
import socket

import pytest

from custom_components.dell_c1760nw.api import oids
from custom_components.dell_c1760nw.api.snmp import DellSnmpClient
from custom_components.dell_c1760nw.api.transport import SnmpClient, SnmpTimeout

from fake_agent import start_agent


def run(coro):
    return asyncio.run(coro)


def printer_oids():
    """Vraies valeurs du snmpwalk d'une C1760nw, aplaties en OID."""
    data = {
        oids.SYS_DESCR: b"Dell C1760nw Color Printer; Net 18.05, Controller 201803071433, Engine 05.09.00",
        oids.IF_PHYS_ADDRESS: bytes.fromhex("080037E0AFF8"),
        oids.HR_PRINTER_STATUS: 3,
        oids.HR_PRINTER_ERROR_STATE: b"\x00\x00",
        oids.PRT_SERIAL: b"ZHD016176",
        oids.PRT_LIFE_COUNT: 1251,
    }
    colors = [(1, b"Cartouche cyan", 700, 105), (2, b"Cartouche magenta", 700, 210),
              (3, b"Cartouche jaune", 700, 210), (4, b"Cartouche noir", 2000, 800)]
    for idx, name, maximum, level in colors:
        base = oids.SUPPLIES_ROOT
        data.update({
            f"{base}.2.1.{idx}": 1, f"{base}.4.1.{idx}": 3, f"{base}.5.1.{idx}": 3,
            f"{base}.6.1.{idx}": name, f"{base}.7.1.{idx}": 7,
            f"{base}.8.1.{idx}": maximum, f"{base}.9.1.{idx}": level,
        })
    a = oids.ALERT_ROOT
    data.update({
        f"{a}.2.1.1": 4, f"{a}.4.1.1": 11, f"{a}.5.1.1": 1, f"{a}.7.1.1": 1104,
        f"{a}.8.1.1": "Remplacer la cartouche de toner cyan bientôt.:093-425".encode(),
        f"{a}.2.1.2": 1, f"{a}.4.1.2": 5, f"{a}.5.1.2": -1, f"{a}.7.1.2": 23,
        f"{a}.8.1.2": "Prêt/Veille".encode(),
    })
    c = oids.COUNTER_ROOT
    for sub, label, value in [("1.20.1", b"Total Impressions", 1251),
                              ("1.20.7", b"Black Printed Impressions", 540),
                              ("1.20.29", b"Color Printed Impressions", 711)]:
        data[f"{c}.6.{sub}"] = value
        data[f"{c}.8.{sub}"] = label
    return data


def test_get_returns_none_for_absent_oids():
    async def main():
        agent, transport, port = await start_agent({"1.3.6.1.2.1.1.1.0": b"x"})
        try:
            client = SnmpClient("127.0.0.1", port, "public")
            return await client.get(["1.3.6.1.2.1.1.1.0", "1.3.6.1.2.1.9.9.9.0"])
        finally:
            transport.close()
    assert run(main()) == {"1.3.6.1.2.1.1.1.0": b"x", "1.3.6.1.2.1.9.9.9.0": None}


def test_walk_spans_several_bulk_requests_and_stops_at_subtree_end():
    data = {f"1.3.6.1.2.1.2.2.1.{col}.{row}": col * 100 + row for col in range(1, 4) for row in range(1, 31)}
    data["1.3.6.1.2.1.4.1.0"] = 99  # hors sous-arbre
    async def main():
        agent, transport, port = await start_agent(data)
        try:
            rows = await SnmpClient("127.0.0.1", port, "public").walk("1.3.6.1.2.1.2.2.1")
            return rows, agent.requests
        finally:
            transport.close()
    rows, requests = run(main())
    assert len(rows) == 90 and requests > 1
    assert all(oid.startswith("1.3.6.1.2.1.2.2.1.") for oid, _ in rows)


def test_retry_recovers_from_a_lost_packet():
    async def main():
        agent, transport, port = await start_agent({"1.3.6.1.2.1.1.1.0": b"ok"}, drop_first=1)
        try:
            client = SnmpClient("127.0.0.1", port, "public", timeout=0.2, retries=1)
            return await client.get(["1.3.6.1.2.1.1.1.0"]), agent.requests
        finally:
            transport.close()
    values, requests = run(main())
    assert values["1.3.6.1.2.1.1.1.0"] == b"ok" and requests == 2


def test_silent_agent_raises_timeout():
    async def main():
        agent, transport, port = await start_agent({}, drop_first=99)
        try:
            await SnmpClient("127.0.0.1", port, "public", timeout=0.1, retries=0).get(["1.3.6.1.2.1.1.1.0"])
        finally:
            transport.close()
    with pytest.raises(SnmpTimeout):
        run(main())


def test_closed_port_fails_fast_with_oserror():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    async def main():
        await SnmpClient("127.0.0.1", port, "public", timeout=1, retries=0).get(["1.3.6.1.2.1.1.1.0"])
    with pytest.raises(OSError):
        run(main())


def test_dell_client_end_to_end_with_real_printer_values():
    async def main():
        agent, transport, port = await start_agent(printer_oids())
        try:
            client = DellSnmpClient("127.0.0.1", port, "public", timeout=0.5, retries=0)
            return await client.async_identify(), await client.async_fetch()
        finally:
            transport.close()
    identity, data = run(main())
    assert identity.serial == "ZHD016176"
    assert data.status == "Prêt"
    assert (data.toner_cyan, data.toner_magenta, data.toner_yellow, data.toner_black) == (15, 30, 30, 40)
    assert data.printer_alert == "Remplacer la cartouche de toner cyan bientôt"
    assert data.alert_code == "093-425"
    assert (data.page_counter_total, data.page_counter_mono, data.page_counter_color) == (1251, 540, 711)
    assert data.mac_address == "08:00:37:e0:af:f8"
    assert data.firmware_version == "Net 18.05, Controller 201803071433, Engine 05.09.00"


def test_dell_client_returns_none_when_printer_is_unreachable():
    async def main():
        agent, transport, port = await start_agent({}, drop_first=99)
        try:
            client = DellSnmpClient("127.0.0.1", port, "public", timeout=0.1, retries=0)
            return await client.async_fetch(), await client.async_identify()
        finally:
            transport.close()
    assert run(main()) == (None, None)
