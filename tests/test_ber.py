"""Codec BER : octets de référence capturés avec un vrai `snmpget` (net-snmp)."""
import pytest

from custom_components.dell_c1760nw.api.ber import (
    END_OF_MIB,
    SnmpError,
    decode_message,
    encode_get,
    encode_oid,
    encode_response,
)

# Capturé avec : snmpget -v2c -c public -d <agent> sysDescr.0 sysUpTime.0
REAL_REQUEST = bytes.fromhex(
    "3037020101040670 75626C6963A02A020474A4187102010002010030 1C300C06082B06010201010100"
    "0500300C06082B060102010103000500".replace(" ", "")
)
REAL_RESPONSE = bytes.fromhex(
    "305E020101040670 75626C6963A251020474A4187102010002010030 43303106082B06010201010100"
    "042544656C6C20433137363 06E7720436F6C6F722050 72696E7465723B204E65742031382E30353 0"
    "0E06082B06010201010300430200C9".replace(" ", "")
)


def test_request_is_byte_identical_to_net_snmp():
    packet = encode_get("public", 0x74A41871, ["1.3.6.1.2.1.1.1.0", "1.3.6.1.2.1.1.3.0"])
    assert packet == REAL_REQUEST


def test_real_response_is_decoded():
    pdu, request_id, status, index, binds = decode_message(REAL_RESPONSE)
    assert (pdu, request_id, status, index) == (0xA2, 0x74A41871, 0, 0)
    assert binds == [
        ("1.3.6.1.2.1.1.1.0", b"Dell C1760nw Color Printer; Net 18.05"),
        ("1.3.6.1.2.1.1.3.0", 201),  # TimeTicks
    ]


def test_roundtrip_values_and_long_lengths():
    long_text = b"x" * 300  # longueur BER sur 2 octets
    oid = "1.3.6.1.4.1.253.8.59.6.1.1.2.1.8.48.48.48.48.48.50.68.68"
    binds = [
        (oid, long_text),
        ("1.3.6.1.2.1.43.11.1.1.9.1.1", 105),
        ("1.3.6.1.2.1.43.8.2.1.10.1.1", -3),
        ("1.3.6.1.2.1.43.11.1.1.9.1.2", 2**31 + 5),
    ]
    _, _, _, _, decoded = decode_message(encode_response("public", 7, binds))
    assert decoded == binds


def test_missing_and_end_of_mib():
    packet = encode_response("public", 1, [("1.3.6.1.2.1.1.1.0", None), ("1.3.6", END_OF_MIB)])
    _, _, _, _, binds = decode_message(packet)
    assert binds[0] == ("1.3.6.1.2.1.1.1.0", None)
    assert binds[1][1] is END_OF_MIB


def test_oid_with_large_arcs():
    assert encode_oid("1.3.6.1.4.1.2699.1") == bytes.fromhex("06 08 2B 06 01 04 01 95 0B 01".replace(" ", ""))
    assert encode_oid("2.999.3") == bytes.fromhex("06 03 88 37 03".replace(" ", ""))
    _, _, _, _, binds = decode_message(encode_response("c", 1, [("2.999.3", 1)]))
    assert binds[0][0] == "2.999.3"


@pytest.mark.parametrize("bad", ["", "1", "abc", "1.x.3", "3.1.2"])
def test_invalid_oid_is_rejected(bad):
    with pytest.raises(SnmpError):
        encode_oid(bad)


def test_truncated_or_garbage_packets_raise():
    for data in (b"", b"\x30", REAL_RESPONSE[:20], b"\x04\x01a", b"\xff" * 10):
        with pytest.raises(SnmpError):
            decode_message(data)
