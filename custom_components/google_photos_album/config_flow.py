"""Config flow for Google Photos Album."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GooglePhotosApiError, GooglePhotosAuthError, GooglePhotosClient
from .const import DOMAIN, SCOPES

_LOGGER = logging.getLogger(__name__)


class _FlowTokenProvider:
    """Access-token provider for validating a freshly completed OAuth flow.

    During async_oauth_create_entry Home Assistant has not created the ConfigEntry yet, so
    OAuth2Session cannot be used safely on newer HA versions where it requires a real
    ConfigEntry. The callback token is fresh enough to validate the Google account email.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    async def async_get_access_token(self) -> str:
        """Return the access token produced by the just-completed OAuth flow."""
        return str(self._data["token"][CONF_ACCESS_TOKEN])


class OAuth2FlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle Google OAuth2 authentication."""

    DOMAIN = DOMAIN
    VERSION = 1
    reauth_entry: ConfigEntry | None = None

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        return {
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        self.reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        if self.reauth_entry:
            self.hass.config_entries.async_update_entry(self.reauth_entry, data=data)
            await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        auth = _FlowTokenProvider(data)
        client = GooglePhotosClient(async_get_clientsession(self.hass), auth)
        try:
            email = await client.get_user_email()
        except GooglePhotosAuthError:
            return self.async_abort(reason="auth_failed")
        except (GooglePhotosApiError, ClientError) as exc:
            return self.async_abort(
                reason="access_error", description_placeholders={"reason": str(exc)}
            )

        await self.async_set_unique_id(email)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=email, data=data, options={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlowHandler:
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options are controlled by entities; this keeps a placeholder options entry."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return self.async_create_entry(title="", data={**self.config_entry.options})
