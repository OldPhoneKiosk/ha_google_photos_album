"""Coordinator for Google Photos Album."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from inspect import signature

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Album, GooglePhotosApiError, GooglePhotosClient, MediaItem
from .const import (
    ALBUM_LIBRARY,
    CONF_ALBUM_ID,
    CONF_ALBUM_TITLE,
    CONF_SELECTION_MODE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_SELECTION_MODE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    INTERVAL_SECONDS,
    MANUFACTURER,
    MODE_RANDOM,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class GooglePhotosAlbumData:
    """Coordinator state."""

    albums: list[Album] = field(default_factory=list)
    media_items: list[MediaItem] = field(default_factory=list)
    current_media: MediaItem | None = None
    selected_album_id: str = ALBUM_LIBRARY
    selected_album_title: str = "All library photos"
    selected_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0))


class GooglePhotosAlbumCoordinator(DataUpdateCoordinator[GooglePhotosAlbumData]):
    """Coordinates albums, media list, and image selection."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: GooglePhotosClient) -> None:
        self.entry = entry
        self.client = client
        self.selection_mode = entry.options.get(CONF_SELECTION_MODE, DEFAULT_SELECTION_MODE)
        self.update_interval_option = entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        self.selected_album_id = entry.options.get(CONF_ALBUM_ID, ALBUM_LIBRARY)
        self.selected_album_title = entry.options.get(CONF_ALBUM_TITLE, "All library photos")
        kwargs = {
            "logger": _LOGGER,
            "name": f"{DOMAIN}_{entry.entry_id}",
            "update_interval": timedelta(minutes=5),
        }
        if "config_entry" in signature(DataUpdateCoordinator.__init__).parameters:
            kwargs["config_entry"] = entry
        super().__init__(hass, **kwargs)

    @property
    def device_info(self) -> DeviceInfo:
        """Return account-level device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=f"Google Photos Album ({self.entry.title})",
        )

    @property
    def album_options(self) -> list[str]:
        """Album titles for select entity."""
        data = self.data
        if not data or not data.albums:
            return [self.selected_album_title]
        return [self._album_label(album) for album in data.albums]

    @property
    def current_album_label(self) -> str:
        """Selected album title label."""
        data = self.data
        if data:
            for album in data.albums:
                if album.id == self.selected_album_id:
                    return self._album_label(album)
        return self.selected_album_title

    async def async_select_album(self, label: str) -> None:
        """Select an album by select option label."""
        if not self.data:
            await self.async_request_refresh()
        assert self.data is not None
        album = next((item for item in self.data.albums if self._album_label(item) == label), None)
        if album is None:
            return
        self.selected_album_id = album.id
        self.selected_album_title = album.title
        self._persist_options()
        await self.async_refresh()

    async def async_select_mode(self, mode: str) -> None:
        """Select image rotation mode."""
        self.selection_mode = mode
        self._persist_options()
        if self.data:
            await self.async_select_next(force=True)

    async def async_select_interval(self, interval: str) -> None:
        """Select image rotation interval."""
        self.update_interval_option = interval
        self._persist_options()
        self.async_update_listeners()

    async def async_select_next(self, *, force: bool = False) -> None:
        """Select next/current image and notify entities."""
        if not self.data or not self.data.media_items:
            await self.async_request_refresh()
            return
        items = self.data.media_items
        if not items:
            return
        if self.selection_mode == MODE_RANDOM:
            current = random.choice(items)
        else:
            current_id = self.data.current_media.id if self.data.current_media else None
            index = next((idx for idx, item in enumerate(items) if item.id == current_id), -1)
            current = items[(index + 1) % len(items)]
        self.data.current_media = current
        self.data.selected_at = datetime.now()
        self.async_update_listeners()

    async def async_camera_image(self, width: int | None, height: int | None) -> bytes | None:
        """Return current camera image bytes."""
        if await self._maybe_rotate() or not self.data or not self.data.current_media:
            if not self.data or not self.data.current_media:
                await self.async_select_next(force=True)
        if not self.data or not self.data.current_media:
            return None
        return await self.client.fetch_image(
            self.data.current_media,
            width=width or 1600,
            height=height or 1200,
        )

    async def _async_update_data(self) -> GooglePhotosAlbumData:
        """Fetch albums and selected album's media."""
        try:
            albums = await self.client.list_albums()
            album = next((item for item in albums if item.id == self.selected_album_id), albums[0])
            self.selected_album_id = album.id
            self.selected_album_title = album.title
            media_items = await self.client.list_media_items(album.id)
        except GooglePhotosApiError as exc:
            raise UpdateFailed(str(exc)) from exc
        data = GooglePhotosAlbumData(
            albums=albums,
            media_items=media_items,
            selected_album_id=album.id,
            selected_album_title=album.title,
        )
        if media_items:
            data.current_media = random.choice(media_items)
            data.selected_at = datetime.now()
        self._persist_options()
        return data

    async def _maybe_rotate(self) -> bool:
        if not self.data:
            await self.async_request_refresh()
            return True
        seconds = INTERVAL_SECONDS.get(self.update_interval_option)
        if seconds is None:
            return False
        if (datetime.now() - self.data.selected_at).total_seconds() >= seconds:
            await self.async_select_next()
            return True
        return False

    def _persist_options(self) -> None:
        options = {**self.entry.options}
        options.update(
            {
                CONF_ALBUM_ID: self.selected_album_id,
                CONF_ALBUM_TITLE: self.selected_album_title,
                CONF_SELECTION_MODE: self.selection_mode,
                CONF_UPDATE_INTERVAL: self.update_interval_option,
            }
        )
        self.hass.config_entries.async_update_entry(self.entry, options=options)

    def _album_label(self, album: Album) -> str:
        count = "?" if album.media_items_count is None else str(album.media_items_count)
        suffix = " shared" if album.shared else ""
        return f"{album.title} ({count} items{suffix})"
