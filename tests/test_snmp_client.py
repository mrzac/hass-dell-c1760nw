"""Teste la logique d'E/S du client SNMP avec une fausse bibliothèque pysnmp."""
import asyncio
from types import SimpleNamespace

from custom_components.dell_c1760nw.api import oids
from custom_components.dell_c1760nw.api.snmp import (
    DellSnmpClient,
    clean_value,
    iter_varbinds,
    oid_text,
)

GET_DATA = {
    oids.SYS_DESCR: "Dell C1760nw Color Printer; Net 18.05",
    oids.PRT_SERIAL: "ZHD016176",
    oids.HR_PRINTER_STATUS: 3,
}
WALK_DATA = {
    oids.SUPPLIES_ROOT: [
        [
            (f"{oids.SUPPLIES_ROOT}.6.1.1", b"Cartouche cyan"),
            (f"{oids.SUPPLIES_ROOT}.9.1.1", 105),
            (f"{oids.SUPPLIES_ROOT}.8.1.1", 700),
            (f"{oids.SUPPLIES_ROOT}.7.1.1", 7),
            (f"{oids.SUPPLIES_ROOT}.5.1.1", 3),
        ],
        # Hors sous-arbre : doit être ignoré.
        [("1.3.6.1.2.1.43.12.1.1.4.1.1", b"cyan")],
    ],
}


class NoSuchInstance:  # même nom de classe que pysnmp
    pass


def make_lib(get_data):
    async def create(addr, timeout, retries):
        return SimpleNamespace(addr=addr)

    async def get_cmd(engine, auth, target, ctx, *varbinds):
        binds = [(vb[0], get_data.get(vb[0], NoSuchInstance())) for vb in varbinds]
        return None, 0, 0, binds

    async def bulk_walk_cmd(engine, auth, target, ctx, nr, mr, varbind, **kw):
        for chunk in WALK_DATA.get(varbind[0], []):
            yield None, 0, 0, chunk

    return SimpleNamespace(
        SnmpEngine=lambda: object(),
        CommunityData=lambda community, mpModel=1: ("community", community),
        ContextData=lambda: None,
        ObjectIdentity=lambda oid: oid,
        ObjectType=lambda identity, value=None: (identity, value),
        UdpTransportTarget=SimpleNamespace(create=create),
        get_cmd=get_cmd,
        bulk_walk_cmd=bulk_walk_cmd,
    )


def make_client(get_data=GET_DATA):
    client = DellSnmpClient("192.168.50.47", 161, "public")
    client._lib = make_lib(get_data)
    client._engine = object()
    return client


def test_fetch_builds_data_from_rows():
    data = asyncio.run(make_client().async_fetch())
    assert data is not None
    assert data.serial_number == "ZHD016176"
    assert data.status == "Prêt"
    assert data.toner_cyan == 15  # 105 / 700
    assert data.toner_black is None


def test_unreachable_printer_returns_none():
    assert asyncio.run(make_client({}).async_fetch()) is None


def test_identify_returns_serial():
    identity = asyncio.run(make_client().async_identify())
    assert identity is not None and identity.serial == "ZHD016176"
    assert asyncio.run(make_client({}).async_identify()) is None


def test_helpers():
    assert clean_value(NoSuchInstance()) is None
    assert clean_value(5) == 5
    assert oid_text(".1.3.6.1") == "1.3.6.1"
    nested = [[("1.2", 1)], ("1.3", 2)]
    assert list(iter_varbinds(nested)) == [("1.2", 1), ("1.3", 2)]
