"""Client SNMP v2c asynchrone (UDP) : GET et parcours de table par GETBULK."""
from __future__ import annotations

import asyncio
import logging
import secrets
from typing import Any

from .ber import (
    END_OF_MIB,
    PDU_RESPONSE,
    SnmpError,
    decode_message,
    encode_get,
    encode_getbulk,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 2.0
DEFAULT_RETRIES = 1
BULK_REPETITIONS = 20
MAX_ROWS = 512


class SnmpTimeout(SnmpError):
    """Aucune réponse de l'agent SNMP."""


class _ResponseProtocol(asyncio.DatagramProtocol):
    """Attend la réponse portant le request-id attendu ; ignore le reste."""

    def __init__(self, request_id: int, future: asyncio.Future) -> None:
        self._request_id = request_id
        self._future = future

    def datagram_received(self, data: bytes, addr: Any) -> None:
        try:
            message = decode_message(data)
        except SnmpError:
            return  # paquet étranger ou corrompu : le délai fera foi
        if message[0] == PDU_RESPONSE and message[1] == self._request_id:
            if not self._future.done():
                self._future.set_result(message)

    def error_received(self, exc: Exception) -> None:
        if not self._future.done():
            self._future.set_exception(exc)


def _oid_key(oid: str) -> tuple[int, ...]:
    return tuple(int(part) for part in oid.split("."))


class SnmpClient:
    """Agent SNMP v2c interrogé en UDP, sans dépendance externe."""

    def __init__(
        self,
        host: str,
        port: int,
        community: str,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        self.host = host
        self.port = port
        self.community = community
        self.timeout = timeout
        self.retries = retries

    async def _exchange(self, request_id: int, packet: bytes):
        loop = asyncio.get_running_loop()
        for attempt in range(self.retries + 1):
            future: asyncio.Future = loop.create_future()
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _ResponseProtocol(request_id, future),
                remote_addr=(self.host, self.port),
            )
            try:
                transport.sendto(packet)
                return await asyncio.wait_for(future, self.timeout)
            except TimeoutError:
                _LOGGER.debug(
                    "SNMP %s:%s sans réponse (essai %s/%s)",
                    self.host,
                    self.port,
                    attempt + 1,
                    self.retries + 1,
                )
            finally:
                transport.close()
        raise SnmpTimeout(f"aucune réponse de {self.host}:{self.port}")

    async def get(self, oid_list: tuple[str, ...] | list[str]) -> dict[str, Any]:
        """GET ; les OID absents valent None."""
        request_id = secrets.randbits(31)
        packet = encode_get(self.community, request_id, list(oid_list))
        _, _, status, index, varbinds = await self._exchange(request_id, packet)
        if status:
            raise SnmpError(f"erreur SNMP {status} (index {index})")
        return {oid: value for oid, value in varbinds}

    async def walk(self, root: str) -> list[tuple[str, Any]]:
        """Parcourt le sous-arbre `root` par GETBULK."""
        prefix = root.strip(".") + "."
        current = root.strip(".")
        rows: list[tuple[str, Any]] = []
        while len(rows) < MAX_ROWS:
            request_id = secrets.randbits(31)
            packet = encode_getbulk(
                self.community, request_id, current, BULK_REPETITIONS
            )
            _, _, status, index, varbinds = await self._exchange(request_id, packet)
            if status:
                raise SnmpError(f"erreur SNMP {status} (index {index})")
            if not varbinds:
                break
            previous = _oid_key(current)
            for oid, value in varbinds:
                if value is END_OF_MIB or not oid.startswith(prefix):
                    return rows
                if _oid_key(oid) <= previous:  # agent défectueux : on évite la boucle
                    return rows
                rows.append((oid, value))
                previous = _oid_key(oid)
                current = oid
        return rows
