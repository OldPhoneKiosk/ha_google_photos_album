"""Application credentials support for Google Photos Album."""

from __future__ import annotations

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return the Google OAuth authorization server."""
    return AuthorizationServer(
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Return placeholders for Home Assistant's application credentials dialog."""
    return {
        "oauth_consent_url": "https://console.cloud.google.com/apis/credentials/consent",
        "oauth_creds_url": "https://console.cloud.google.com/apis/credentials",
        "more_info_url": "https://github.com/OldPhoneKiosk/ha_google_photos_album",
    }
