"""Coordinator for Google Photos Album Picker collections."""

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

from .api import (
    GooglePhotosApiError,
    GooglePhotosClient,
    GooglePhotosMediaCache,
    MediaItem,
    PickerNotReadyError,
    PickerSession,
)
from .const import (
    CONF_PICKED_MEDIA,
    CONF_PICKER_EXPIRE_TIME,
    CONF_PICKER_SESSION_ID,
    CONF_PICKER_URI,
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

    media_items: list[MediaItem] = field(default_factory=list)
    current_media: MediaItem | None = None
    selected_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0))
    picker_session_id: str | None = None
    picker_uri: str | None = None
    picker_expire_time: str | None = None
    picker_media_items_set: bool = False


class GooglePhotosAlbumCoordinator(DataUpdateCoordinator[GooglePhotosAlbumData]):
    """Coordinates picker sessions, cached selections, and image rotation."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: GooglePhotosClient) -> None:
        self.entry = entry
        self.client = client
        self.cache = GooglePhotosMediaCache(hass.config.path(".storage", DOMAIN, entry.entry_id))
        self.selection_mode = entry.options.get(CONF_SELECTION_MODE, DEFAULT_SELECTION_MODE)
        self.update_interval_option = entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
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
            name=f"Google Photos Picker ({self.entry.title})",
        )

    @property
    def picker_uri(self) -> str | None:
        """Return latest picker URI."""
        if self.data and self.data.picker_uri:
            return self.data.picker_uri
        return self.entry.options.get(CONF_PICKER_URI)

    @property
    def picker_session_id(self) -> str | None:
        """Return latest picker session id."""
        if self.data and self.data.picker_session_id:
            return self.data.picker_session_id
        return self.entry.options.get(CONF_PICKER_SESSION_ID)

    async def async_create_picker_session(self) -> PickerSession:
        """Create a new Picker API session and persist its URI."""
        session = await self.client.create_picker_session()
        data = self.data or GooglePhotosAlbumData(media_items=self._load_cached_media())
        data.picker_session_id = session.id
        data.picker_uri = session.picker_uri or data.picker_uri
        data.picker_expire_time = session.expire_time
        data.picker_media_items_set = session.media_items_set
        self.data = data
        self._persist_options()
        self.async_update_listeners()
        return session

    async def async_poll_picker_session(self) -> PickerSession | None:
        """Poll latest picker session and update readiness status."""
        session_id = self.picker_session_id
        if not session_id:
            return None
        session = await self.client.get_picker_session(session_id)
        data = self.data or GooglePhotosAlbumData(media_items=self._load_cached_media())
        data.picker_session_id = session.id
        data.picker_uri = session.picker_uri or data.picker_uri
        data.picker_expire_time = session.expire_time
        data.picker_media_items_set = session.media_items_set
        self.data = data
        self._persist_options()
        self.async_update_listeners()
        return session

    async def async_import_picked_media(self) -> int:
        """Import media from the latest completed picker session into cached selection."""
        session_id = self.picker_session_id
        if not session_id:
            return 0
        await self.async_poll_picker_session()
        try:
            picked = await self.client.list_picked_media_items(session_id)
        except PickerNotReadyError:
            return 0
        cached_picked: list[MediaItem] = []
        for item in picked:
            try:
                image = await self.client.fetch_image(item)
                item = await self.cache.async_store(item, image)
            except GooglePhotosApiError:
                _LOGGER.warning(
                    "Could not cache picked Google Photos media %s; it may expire",
                    item.id,
                    exc_info=True,
                )
            cached_picked.append(item)
        data = self.data or GooglePhotosAlbumData()
        replaced_media_ids = {item.id for item in cached_picked}
        for item in data.media_items:
            if item.id not in replaced_media_ids:
                self.cache.delete(item)
        data.media_items = cached_picked
        data.current_media = random.choice(data.media_items) if data.media_items else None
        data.selected_at = datetime.now()
        self.data = data
        self._persist_options()
        try:
            await self.client.delete_picker_session(session_id)
            data.picker_session_id = None
            data.picker_uri = None
            data.picker_expire_time = None
            data.picker_media_items_set = False
        except GooglePhotosApiError:
            _LOGGER.debug("Could not delete picker session %s", session_id, exc_info=True)
        self._persist_options()
        self.async_update_listeners()
        return len(picked)

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
        if not self.data:
            await self.async_request_refresh()
        if not self.data or not self.data.media_items:
            return
        items = self.data.media_items
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
        cached = self.cache.read(self.data.current_media)
        if cached:
            return cached
        image = await self.client.fetch_image(
            self.data.current_media,
            width=width or 1600,
            height=height or 1200,
        )
        if not self.data.current_media.cached_path:
            try:
                self.data.current_media = await self.cache.async_store(
                    self.data.current_media, image
                )
                self._persist_options()
            except OSError:
                _LOGGER.debug("Could not backfill Google Photos media cache", exc_info=True)
        return image

    async def _async_update_data(self) -> GooglePhotosAlbumData:
        """Load cached media and poll picker session status."""
        try:
            cached = self._load_cached_media()
            session_id = self.entry.options.get(CONF_PICKER_SESSION_ID)
            picker_uri = self.entry.options.get(CONF_PICKER_URI)
            picker_expire_time = self.entry.options.get(CONF_PICKER_EXPIRE_TIME)
            picker_media_items_set = False
            if session_id:
                session = await self.client.get_picker_session(session_id)
                picker_uri = session.picker_uri or picker_uri
                picker_expire_time = session.expire_time
                picker_media_items_set = session.media_items_set
        except GooglePhotosApiError as exc:
            raise UpdateFailed(str(exc)) from exc
        data = GooglePhotosAlbumData(
            media_items=cached,
            picker_session_id=session_id,
            picker_uri=picker_uri,
            picker_expire_time=picker_expire_time,
            picker_media_items_set=picker_media_items_set,
        )
        if cached:
            current = None
            if self.data and self.data.current_media:
                current = next(
                    (item for item in cached if item.id == self.data.current_media.id), None
                )
            data.current_media = current or cached[0]
            data.selected_at = self.data.selected_at if self.data else datetime.now()
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

    def _load_cached_media(self) -> list[MediaItem]:
        raw = self.entry.options.get(CONF_PICKED_MEDIA, [])
        return [MediaItem.from_json(item) for item in raw if isinstance(item, dict)]

    def _persist_options(self) -> None:
        data = self.data
        options = {**self.entry.options}
        options.update(
            {
                CONF_SELECTION_MODE: self.selection_mode,
                CONF_UPDATE_INTERVAL: self.update_interval_option,
            }
        )
        if data:
            options.update(
                {
                    CONF_PICKED_MEDIA: [item.to_json() for item in data.media_items],
                    CONF_PICKER_SESSION_ID: data.picker_session_id,
                    CONF_PICKER_URI: data.picker_uri,
                    CONF_PICKER_EXPIRE_TIME: data.picker_expire_time,
                }
            )
        self.hass.config_entries.async_update_entry(self.entry, options=options)
