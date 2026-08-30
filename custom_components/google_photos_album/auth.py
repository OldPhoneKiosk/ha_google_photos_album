"""OAuth token wrapper for Google Photos Album."""

from __future__ import annotations

from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session


class GooglePhotosAuth:
    """Expose HA OAuth2Session as a token provider for the REST client."""

    def __init__(self, oauth_session: OAuth2Session) -> None:
        self.oauth_session = oauth_session

    async def async_get_access_token(self) -> str:
        """Return a refreshed access token."""
        await self.oauth_session.async_ensure_token_valid()
        return str(self.oauth_session.token[CONF_ACCESS_TOKEN])
