"""Flux de configuration UI pour Dell C1760nw."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

try:  # Home Assistant >= 2025.2
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
except ImportError:  # versions antérieures
    from homeassistant.components.zeroconf import ZeroconfServiceInfo

from .api.snmp import DellSnmpClient, PrinterIdentity
from .const import CONF_SNMP_COMMUNITY, DEFAULT_COMMUNITY, DEFAULT_PORT, DOMAIN, LOGGER


class DellC1760nwConfigFlow(ConfigFlow, domain=DOMAIN):
    """Gère le formulaire d'ajout et la validation SNMP réelle."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_host: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Étape de configuration manuelle."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            community = user_input.get(CONF_SNMP_COMMUNITY, DEFAULT_COMMUNITY)
            self._async_abort_entries_match({CONF_HOST: host})

            identity = await self._async_identify(host, port, community)
            if identity is None:
                errors["base"] = "cannot_connect"
            else:
                # Le numéro de série reste stable si l'IP change (DHCP).
                await self.async_set_unique_id(identity.serial or host)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=f"Dell C1760nw ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_SNMP_COMMUNITY: community,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=self._discovered_host or vol.UNDEFINED
                ): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    int, vol.Range(min=1, max=65535)
                ),
                vol.Optional(CONF_SNMP_COMMUNITY, default=DEFAULT_COMMUNITY): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Découverte mDNS : n'accepte que les C1760nw et demande confirmation."""
        host = discovery_info.host
        haystack = " ".join(
            [
                discovery_info.name,
                discovery_info.hostname,
                *(str(value) for value in discovery_info.properties.values()),
            ]
        ).lower()
        if "c1760" not in haystack:
            return self.async_abort(reason="not_supported")

        self._async_abort_entries_match({CONF_HOST: host})
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()

        self._discovered_host = host
        self.context["title_placeholders"] = {"host": host}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirmation de l'imprimante découverte."""
        if user_input is not None:
            return await self.async_step_user(
                {CONF_HOST: self._discovered_host, CONF_PORT: DEFAULT_PORT}
            )
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"host": self._discovered_host or ""},
        )

    async def _async_identify(
        self, host: str, port: int, community: str
    ) -> PrinterIdentity | None:
        """Interroge réellement l'imprimante en SNMP (hôte, port et communauté)."""
        client = DellSnmpClient(host, port, community)
        try:
            return await client.async_identify()
        except Exception:  # noqa: BLE001 - toute erreur = échec de connexion
            LOGGER.debug("Validation SNMP de %s impossible", host, exc_info=True)
            return None
