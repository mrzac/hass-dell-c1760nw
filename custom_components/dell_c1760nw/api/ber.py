"""Codec SNMP v2c minimal (BER) : GET, GETBULK et réponses.

Sans dépendance externe : évite tout conflit avec les versions de pysnmp/pyasn1
déjà imposées par Home Assistant.
"""
from __future__ import annotations

from typing import Any

SNMP_V2C = 1

TAG_INTEGER = 0x02
TAG_OCTET_STRING = 0x04
TAG_NULL = 0x05
TAG_OID = 0x06
TAG_SEQUENCE = 0x30
TAG_IPADDRESS = 0x40
TAG_COUNTER32 = 0x41
TAG_GAUGE32 = 0x42
TAG_TIMETICKS = 0x43
TAG_OPAQUE = 0x44
TAG_COUNTER64 = 0x46
TAG_NO_SUCH_OBJECT = 0x80
TAG_NO_SUCH_INSTANCE = 0x81
TAG_END_OF_MIB_VIEW = 0x82

PDU_GET = 0xA0
PDU_RESPONSE = 0xA2
PDU_GETBULK = 0xA5

_UNSIGNED_TAGS = {TAG_COUNTER32, TAG_GAUGE32, TAG_TIMETICKS, TAG_COUNTER64}


class SnmpError(Exception):
    """Réponse SNMP invalide ou en erreur."""


class _EndOfMib:
    """Marqueur « fin de la MIB » (endOfMibView)."""

    def __repr__(self) -> str:
        return "END_OF_MIB"


END_OF_MIB = _EndOfMib()


# --------------------------------------------------------------------------- #
# Encodage
# --------------------------------------------------------------------------- #
def _encode_length(length: int) -> bytes:
    if length < 0x80:
        return bytes([length])
    raw = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _tlv(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _encode_length(len(content)) + content


def encode_integer(value: int) -> bytes:
    """INTEGER signé, complément à deux minimal."""
    length = max(1, (value.bit_length() + 8) // 8)
    return _tlv(TAG_INTEGER, value.to_bytes(length, "big", signed=True))


def encode_oid(oid: str) -> bytes:
    """OID `1.3.6.1…` -> TLV."""
    try:
        arcs = [int(part) for part in oid.strip(".").split(".")]
    except ValueError as err:
        raise SnmpError(f"OID invalide : {oid!r}") from err
    if len(arcs) < 2 or arcs[0] > 2 or arcs[1] < 0 or any(a < 0 for a in arcs):
        raise SnmpError(f"OID invalide : {oid!r}")
    subids = [arcs[0] * 40 + arcs[1], *arcs[2:]]
    body = bytearray()
    for subid in subids:
        chunk = [subid & 0x7F]
        subid >>= 7
        while subid:
            chunk.append(0x80 | (subid & 0x7F))
            subid >>= 7
        body.extend(reversed(chunk))
    return _tlv(TAG_OID, bytes(body))


def encode_value(value: Any) -> bytes:
    """Valeur de réponse (utilisé par les tests et agents simulés)."""
    if value is None:
        return _tlv(TAG_NO_SUCH_INSTANCE, b"")
    if value is END_OF_MIB:
        return _tlv(TAG_END_OF_MIB_VIEW, b"")
    if isinstance(value, bool):
        raise SnmpError("booléen non supporté")
    if isinstance(value, int):
        return encode_integer(value)
    if isinstance(value, (bytes, bytearray)):
        return _tlv(TAG_OCTET_STRING, bytes(value))
    if isinstance(value, str):
        return _tlv(TAG_OCTET_STRING, value.encode("utf-8"))
    raise SnmpError(f"type non supporté : {type(value).__name__}")


def _varbind_list(items: list[bytes]) -> bytes:
    return _tlv(TAG_SEQUENCE, b"".join(items))


def _message(community: str, pdu_tag: int, fields: bytes, varbinds: bytes) -> bytes:
    pdu = _tlv(pdu_tag, fields + varbinds)
    return _tlv(
        TAG_SEQUENCE,
        encode_integer(SNMP_V2C) + _tlv(TAG_OCTET_STRING, community.encode()) + pdu,
    )


def encode_get(community: str, request_id: int, oids: list[str]) -> bytes:
    """Requête GET pour une liste d'OID."""
    varbinds = _varbind_list(
        [_tlv(TAG_SEQUENCE, encode_oid(oid) + _tlv(TAG_NULL, b"")) for oid in oids]
    )
    fields = encode_integer(request_id) + encode_integer(0) + encode_integer(0)
    return _message(community, PDU_GET, fields, varbinds)


def encode_getbulk(
    community: str, request_id: int, oid: str, max_repetitions: int
) -> bytes:
    """Requête GETBULK (0 non-répétiteur) à partir d'un OID."""
    varbinds = _varbind_list([_tlv(TAG_SEQUENCE, encode_oid(oid) + _tlv(TAG_NULL, b""))])
    fields = (
        encode_integer(request_id)
        + encode_integer(0)
        + encode_integer(max_repetitions)
    )
    return _message(community, PDU_GETBULK, fields, varbinds)


def encode_response(
    community: str, request_id: int, varbinds: list[tuple[str, Any]]
) -> bytes:
    """Réponse GET-RESPONSE (agents simulés des tests)."""
    items = [
        _tlv(TAG_SEQUENCE, encode_oid(oid) + encode_value(value))
        for oid, value in varbinds
    ]
    fields = encode_integer(request_id) + encode_integer(0) + encode_integer(0)
    return _message(community, PDU_RESPONSE, fields, _varbind_list(items))


# --------------------------------------------------------------------------- #
# Décodage
# --------------------------------------------------------------------------- #
def _read_tlv(data: bytes, pos: int) -> tuple[int, int, int]:
    """Retourne (tag, début du contenu, fin du contenu)."""
    if pos + 2 > len(data):
        raise SnmpError("paquet tronqué")
    tag = data[pos]
    first = data[pos + 1]
    pos += 2
    if first < 0x80:
        length = first
    else:
        count = first & 0x7F
        if count == 0 or count > 4 or pos + count > len(data):
            raise SnmpError("longueur BER invalide")
        length = int.from_bytes(data[pos : pos + count], "big")
        pos += count
    end = pos + length
    if end > len(data):
        raise SnmpError("paquet tronqué")
    return tag, pos, end


def _decode_int(content: bytes, *, signed: bool) -> int:
    if not content:
        raise SnmpError("entier vide")
    return int.from_bytes(content, "big", signed=signed)


def _decode_oid(content: bytes) -> str:
    if not content:
        raise SnmpError("OID vide")
    subids: list[int] = []
    value = 0
    for byte in content:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            subids.append(value)
            value = 0
    if content[-1] & 0x80:
        raise SnmpError("OID tronqué")
    first = subids[0]
    head = [first // 40, first % 40] if first < 80 else [2, first - 80]
    return ".".join(str(arc) for arc in [*head, *subids[1:]])


def decode_value(tag: int, content: bytes) -> Any:
    """Valeur Python : int, bytes, str (OID/IP), None (absent) ou END_OF_MIB."""
    if tag == TAG_INTEGER:
        return _decode_int(content, signed=True)
    if tag in _UNSIGNED_TAGS:
        return _decode_int(content, signed=False)
    if tag in (TAG_OCTET_STRING, TAG_OPAQUE):
        return bytes(content)
    if tag == TAG_NULL:
        return None
    if tag == TAG_OID:
        return _decode_oid(content)
    if tag == TAG_IPADDRESS and len(content) == 4:
        return ".".join(str(b) for b in content)
    if tag in (TAG_NO_SUCH_OBJECT, TAG_NO_SUCH_INSTANCE):
        return None
    if tag == TAG_END_OF_MIB_VIEW:
        return END_OF_MIB
    return bytes(content)


def decode_message(data: bytes) -> tuple[int, int, int, int, list[tuple[str, Any]]]:
    """Décode un message : (type de PDU, request-id, erreur, index, varbinds)."""
    tag, pos, end = _read_tlv(data, 0)
    if tag != TAG_SEQUENCE:
        raise SnmpError("message SNMP invalide")
    tag, start, stop = _read_tlv(data, pos)
    if tag != TAG_INTEGER or _decode_int(data[start:stop], signed=True) != SNMP_V2C:
        raise SnmpError("version SNMP non supportée")
    tag, start, pos = _read_tlv(data, stop)
    if tag != TAG_OCTET_STRING:
        raise SnmpError("communauté absente")
    pdu_tag, pdu_start, pdu_end = _read_tlv(data, pos)

    cursor = pdu_start
    ints: list[int] = []
    for _ in range(3):
        tag, start, stop = _read_tlv(data, cursor)
        if tag != TAG_INTEGER:
            raise SnmpError("en-tête PDU invalide")
        ints.append(_decode_int(data[start:stop], signed=True))
        cursor = stop

    tag, list_start, list_end = _read_tlv(data, cursor)
    if tag != TAG_SEQUENCE:
        raise SnmpError("liste de varbinds invalide")
    varbinds: list[tuple[str, Any]] = []
    cursor = list_start
    while cursor < list_end:
        tag, start, stop = _read_tlv(data, cursor)
        if tag != TAG_SEQUENCE:
            raise SnmpError("varbind invalide")
        tag, o_start, o_end = _read_tlv(data, start)
        if tag != TAG_OID:
            raise SnmpError("OID de varbind invalide")
        oid = _decode_oid(data[o_start:o_end])
        v_tag, v_start, v_end = _read_tlv(data, o_end)
        varbinds.append((oid, decode_value(v_tag, data[v_start:v_end])))
        cursor = stop
    return pdu_tag, ints[0], ints[1], ints[2], varbinds
