"""Minimal asyncio SNMP v2c client (GET / GETNEXT), no external dependency."""
from __future__ import annotations

import asyncio
import random
from typing import Any

GET_REQUEST = 0xA0
GETNEXT_REQUEST = 0xA1
NO_SUCH_NAME = 2


class SnmpError(Exception):
    """SNMP communication problem (status = SNMP error-status if any)."""

    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


def _enc_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _enc_len(len(value)) + value


def _enc_int(n: int) -> bytes:
    length = max(1, (n.bit_length() + 8) // 8)
    return _tlv(0x02, n.to_bytes(length, "big", signed=True))


def _enc_oid(oid: str) -> bytes:
    parts = [int(p) for p in oid.strip(".").split(".")]
    body = bytearray([parts[0] * 40 + parts[1]])
    for p in parts[2:]:
        chunk = [p & 0x7F]
        p >>= 7
        while p:
            chunk.append(0x80 | (p & 0x7F))
            p >>= 7
        body.extend(reversed(chunk))
    return _tlv(0x06, bytes(body))


def build_request(community: str, oids: list[str], request_id: int, pdu_tag: int = GET_REQUEST) -> bytes:
    varbinds = b"".join(_tlv(0x30, _enc_oid(o) + b"\x05\x00") for o in oids)
    pdu = _tlv(
        pdu_tag,
        _enc_int(request_id) + _enc_int(0) + _enc_int(0) + _tlv(0x30, varbinds),
    )
    return _tlv(0x30, _enc_int(1) + _tlv(0x04, community.encode()) + pdu)


def _read_tlv(data: bytes, pos: int) -> tuple[int, bytes, int]:
    tag = data[pos]
    length = data[pos + 1]
    pos += 2
    if length & 0x80:
        n = length & 0x7F
        length = int.from_bytes(data[pos : pos + n], "big")
        pos += n
    end = pos + length
    if end > len(data):
        raise SnmpError("Truncated SNMP packet")
    return tag, data[pos:end], end


def _dec_oid(b: bytes) -> str:
    parts = [str(b[0] // 40), str(b[0] % 40)]
    val = 0
    for byte in b[1:]:
        val = (val << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(str(val))
            val = 0
    return ".".join(parts)


def _dec_value(tag: int, v: bytes) -> Any:
    if tag == 0x02:
        return int.from_bytes(v, "big", signed=True) if v else 0
    if tag in (0x41, 0x42, 0x43, 0x46):
        return int.from_bytes(v, "big", signed=False) if v else 0
    if tag == 0x04:
        return v.decode("utf-8", errors="replace").replace("\x00", "").strip()
    if tag == 0x06:
        return _dec_oid(v)
    if tag == 0x40 and len(v) == 4:
        return ".".join(str(x) for x in v)
    if tag in (0x80, 0x81, 0x82) or tag == 0x05:
        return None  # noSuchObject / noSuchInstance / endOfMibView / NULL
    return v


def parse_response(data: bytes, request_id: int) -> dict[str, Any]:
    try:
        _, msg, _ = _read_tlv(data, 0)
        _, _, pos = _read_tlv(msg, 0)  # version
        _, _, pos = _read_tlv(msg, pos)  # community
        tag, pdu, _ = _read_tlv(msg, pos)
        if tag != 0xA2:
            raise SnmpError(f"Unexpected PDU type {tag:#x}")
        _, rid, pos = _read_tlv(pdu, 0)
        if int.from_bytes(rid, "big", signed=True) != request_id:
            raise SnmpError("Mismatched request id")
        _, err, pos = _read_tlv(pdu, pos)
        status = int.from_bytes(err, "big")
        if status:
            raise SnmpError(f"SNMP error status {status}", status)
        _, _, pos = _read_tlv(pdu, pos)  # error index
        _, vbl, _ = _read_tlv(pdu, pos)
        result: dict[str, Any] = {}
        pos = 0
        while pos < len(vbl):
            _, vb, pos = _read_tlv(vbl, pos)
            _, oid_b, p = _read_tlv(vb, 0)
            vtag, vval, _ = _read_tlv(vb, p)
            result[_dec_oid(oid_b)] = _dec_value(vtag, vval)
        return result
    except (IndexError, ValueError) as err:
        raise SnmpError(f"Malformed SNMP packet: {err}") from err


class _Proto(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.future: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

    def datagram_received(self, data: bytes, addr) -> None:
        if not self.future.done():
            self.future.set_result(data)

    def error_received(self, exc: Exception) -> None:
        if not self.future.done():
            self.future.set_exception(SnmpError(str(exc)))


async def _request(host, community, port, oids, pdu_tag, timeout, retries) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    last: Exception | None = None
    for _ in range(retries + 1):
        request_id = random.randint(1, 0x7FFFFFFF)
        packet = build_request(community, oids, request_id, pdu_tag)
        try:
            transport, proto = await loop.create_datagram_endpoint(
                _Proto, remote_addr=(host, port)
            )
        except OSError as err:
            raise SnmpError(str(err)) from err
        try:
            transport.sendto(packet)
            data = await asyncio.wait_for(proto.future, timeout)
            return parse_response(data, request_id)
        except asyncio.TimeoutError:
            last = SnmpError("Timeout")
        finally:
            transport.close()
    raise last or SnmpError("Unknown error")


async def snmp_get(
    host: str,
    oids: list[str],
    community: str = "public",
    port: int = 161,
    timeout: float = 5.0,
    retries: int = 2,
    chunk: int = 10,
) -> dict[str, Any]:
    """SNMP v2c GET in small batches. Missing objects are returned as None."""
    result: dict[str, Any] = {}
    for i in range(0, len(oids), chunk):
        batch = oids[i : i + chunk]
        try:
            result.update(await _request(host, community, port, batch, GET_REQUEST, timeout, retries))
        except SnmpError as err:
            if err.status != NO_SUCH_NAME or len(batch) == 1:
                if err.status == NO_SUCH_NAME:
                    result[batch[0]] = None
                    continue
                raise
            # Agent rejects the whole PDU when one OID is missing: go one by one.
            for oid in batch:
                try:
                    result.update(await _request(host, community, port, [oid], GET_REQUEST, timeout, retries))
                except SnmpError as err2:
                    if err2.status != NO_SUCH_NAME:
                        raise
                    result[oid] = None
    return result


async def snmp_walk(
    host: str,
    base: str,
    community: str = "public",
    port: int = 161,
    timeout: float = 5.0,
    retries: int = 2,
    max_items: int = 32,
) -> dict[str, Any]:
    """Walk a (small) subtree with GETNEXT."""
    out: dict[str, Any] = {}
    cur = base
    for _ in range(max_items):
        try:
            res = await _request(host, community, port, [cur], GETNEXT_REQUEST, timeout, retries)
        except SnmpError as err:
            if err.status == NO_SUCH_NAME:
                break
            raise
        if not res:
            break
        oid, val = next(iter(res.items()))
        if not oid.startswith(base + ".") or val is None:
            break
        out[oid] = val
        cur = oid
    return out
