"""Google Photos Album integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import DOMAIN, PLATFORMS

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Google Photos Album from a config entry."""
    from aiohttp import ClientError, ClientResponseError
    from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.helpers.config_entry_oauth2_flow import (
        OAuth2Session,
        async_get_config_entry_implementation,
    )

    from .api import GooglePhotosAuthError, GooglePhotosClient
    from .auth import GooglePhotosAuth
    from .coordinator import GooglePhotosAlbumCoordinator

    implementation = await async_get_config_entry_implementation(hass, entry)
    oauth_session = OAuth2Session(hass, entry, implementation)
    auth = GooglePhotosAuth(oauth_session)
    client = GooglePhotosClient(async_get_clientsession(hass), auth)
    try:
        await auth.async_get_access_token()
    except ClientResponseError as err:
        if 400 <= err.status < 500:
            raise ConfigEntryAuthFailed("Google OAuth session is invalid") from err
        raise ConfigEntryNotReady from err
    except ClientError as err:
        raise ConfigEntryNotReady from err

    coordinator = GooglePhotosAlbumCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except GooglePhotosAuthError as err:
        raise ConfigEntryAuthFailed("Google Photos authorization failed") from err
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
