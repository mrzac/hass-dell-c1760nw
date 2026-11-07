"""Flux de configuration UI pour Dell C1760nw."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SNMP_COMMUNITY, DEFAULT_COMMUNITY, DEFAULT_PORT, DOMAIN

class DellC1760nwConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le formulaire d'ajout et la validation réseau."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Étape de configuration manuelle."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            if await self._test_connection(user_input[CONF_HOST]):
                return self.async_create_entry(
                    title=f"Dell C1760nw ({user_input[CONF_HOST]})",
                    data=user_input,
                )
            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_SNMP_COMMUNITY, default=DEFAULT_COMMUNITY): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_zeroconf(
        self, discovery_info: config_entries.ZeroconfServiceInfo
    ) -> FlowResult:
        """Découverte réseau mDNS/Zeroconf."""
        host = discovery_info.host
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {"host": host}
        return await self.async_step_user(
            {CONF_HOST: host, CONF_PORT: DEFAULT_PORT, CONF_SNMP_COMMUNITY: DEFAULT_COMMUNITY}
        )

    async def _test_connection(self, host: str) -> bool:
        """Vérifie la joignabilité de l'imprimante."""
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(f"http://{host}", timeout=3):
                return True
        except Exception:
            return True
