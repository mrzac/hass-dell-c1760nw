"""Faux agent SNMP UDP (GET / GETBULK) pour tester le client sans réseau réel."""
from __future__ import annotations

import asyncio
from typing import Any

from custom_components.dell_c1760nw.api.ber import (
    END_OF_MIB,
    PDU_GET,
    decode_message,
    encode_response,
)


def oid_key(oid: str) -> tuple[int, ...]:
    return tuple(int(p) for p in oid.split("."))


class FakeAgent(asyncio.DatagramProtocol):
    def __init__(self, data: dict[str, Any], drop_first: int = 0) -> None:
        self.data = data
        self.order = sorted(data, key=oid_key)
        self.drop_first = drop_first
        self.requests = 0
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport) -> None:
        self.transport = transport

    def datagram_received(self, packet: bytes, addr) -> None:
        self.requests += 1
        if self.requests <= self.drop_first:
            return
        pdu, request_id, _nonrep, max_rep, binds = decode_message(packet)
        if pdu == PDU_GET:
            out = [(oid, self.data.get(oid)) for oid, _ in binds]
        else:  # GETBULK
            start = oid_key(binds[0][0])
            out = []
            for oid in self.order:
                if oid_key(oid) > start:
                    out.append((oid, self.data[oid]))
                if len(out) >= max_rep:
                    break
            if not out:
                out = [(binds[0][0], END_OF_MIB)]
        assert self.transport is not None
        self.transport.sendto(encode_response("public", request_id, out), addr)


async def start_agent(data: dict[str, Any], drop_first: int = 0):
    loop = asyncio.get_running_loop()
    agent = FakeAgent(data, drop_first)
    transport, _ = await loop.create_datagram_endpoint(
        lambda: agent, local_addr=("127.0.0.1", 0)
    )
    return agent, transport, transport.get_extra_info("sockname")[1]
