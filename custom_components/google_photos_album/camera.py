"""Camera platform for Google Photos Album."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components.camera import Camera, CameraEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MODE_OPTIONS
from .coordinator import GooglePhotosAlbumCoordinator

_LOGGER = logging.getLogger(__name__)
SERVICE_NEXT_PHOTO = "next_photo"
ATTR_MODE = "mode"
NEXT_PHOTO_SCHEMA = {vol.Optional(ATTR_MODE): vol.In(MODE_OPTIONS)}
CAMERA_DESCRIPTION = CameraEntityDescription(key="media", name="Media", icon="mdi:google-photos")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up camera entity."""
    coordinator: GooglePhotosAlbumCoordinator = hass.data[DOMAIN][entry.entry_id]
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_NEXT_PHOTO, NEXT_PHOTO_SCHEMA, "async_next_photo"
    )
    async_add_entities([GooglePhotosAlbumCamera(coordinator)])


class GooglePhotosAlbumCamera(Camera):
    """Camera exposing the currently selected Google Photos image."""

    _attr_has_entity_name = True
    _attr_entity_description = CAMERA_DESCRIPTION

    def __init__(self, coordinator: GooglePhotosAlbumCoordinator) -> None:
        super().__init__()
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_media"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_coordinator_update))
        self._handle_coordinator_update()

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        data = self.coordinator.data
        media = data.current_media if data else None
        return {
            "media_id": media.id if media else None,
            "filename": media.filename if media else None,
            "creation_time": media.creation_time if media else None,
            "media_count": len(data.media_items) if data else 0,
            "picker_session_id": data.picker_session_id if data else None,
            "picker_ready": data.picker_media_items_set if data else False,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_update(self) -> None:
        await self.coordinator.async_request_refresh()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        try:
            return await self.coordinator.async_camera_image(width, height)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("Failed to fetch Google Photos image: %s", exc)
            return None

    async def async_next_photo(self, mode: str | None = None) -> None:
        if mode:
            await self.coordinator.async_select_mode(mode)
        await self.coordinator.async_select_next(force=True)
