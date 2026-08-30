"""Google Photos REST client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import aiohttp

from .const import ALBUM_LIBRARY, GOOGLE_PHOTOS_API, GOOGLE_USERINFO_URL


class GooglePhotosError(Exception):
    """Base Google Photos Album error."""


class GooglePhotosAuthError(GooglePhotosError):
    """OAuth token is invalid or lacks access."""


class GooglePhotosApiError(GooglePhotosError):
    """Google Photos API request failed."""


class AccessTokenProvider(Protocol):
    """Provider of valid OAuth access tokens."""

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""


@dataclass(slots=True, frozen=True)
class Album:
    """Google Photos album metadata."""

    id: str
    title: str
    media_items_count: int | None = None
    product_url: str | None = None
    shared: bool = False


@dataclass(slots=True, frozen=True)
class MediaItem:
    """Google Photos media item metadata."""

    id: str
    filename: str
    base_url: str
    mime_type: str
    product_url: str | None = None
    creation_time: str | None = None
    width: str | None = None
    height: str | None = None


class GooglePhotosClient:
    """Small async client for Google Photos Library API."""

    def __init__(self, session: aiohttp.ClientSession, token_provider: AccessTokenProvider) -> None:
        self._session = session
        self._token_provider = token_provider

    async def get_user_email(self) -> str:
        """Return authenticated account email."""
        data = await self._request_url("GET", GOOGLE_USERINFO_URL)
        return str(data.get("email") or "Google Photos")

    async def list_albums(self) -> list[Album]:
        """List normal and shared albums visible to the user."""
        albums = [Album(id=ALBUM_LIBRARY, title="All library photos", shared=False)]
        albums.extend(await self._list_albums_endpoint("albums", shared=False))
        albums.extend(await self._list_albums_endpoint("sharedAlbums", shared=True))
        seen: set[str] = set()
        unique: list[Album] = []
        for album in albums:
            if album.id in seen:
                continue
            seen.add(album.id)
            unique.append(album)
        return unique

    async def list_media_items(self, album_id: str) -> list[MediaItem]:
        """List media items for album or whole library."""
        items: list[MediaItem] = []
        page_token: str | None = None
        while True:
            if album_id == ALBUM_LIBRARY:
                path = "/mediaItems"
                body = None
                params = {"pageSize": "100"}
                if page_token:
                    params["pageToken"] = page_token
                result = await self._request("GET", path, params=params)
            else:
                body = {"albumId": album_id, "pageSize": 100}
                if page_token:
                    body["pageToken"] = page_token
                result = await self._request("POST", "/mediaItems:search", json=body)
            items.extend(_media_item_from_json(item) for item in result.get("mediaItems", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return [item for item in items if item.mime_type.startswith("image/")]

    async def fetch_image(self, media: MediaItem, width: int = 1600, height: int = 1200) -> bytes:
        """Fetch image bytes from a short-lived Google Photos baseUrl."""
        transform = f"=w{max(width, 1)}-h{max(height, 1)}"
        url = f"{media.base_url}{transform}"
        async with self._session.get(url) as resp:
            if resp.status in {401, 403}:
                raise GooglePhotosAuthError(await resp.text())
            if resp.status >= 400:
                raise GooglePhotosApiError(f"Google image fetch {resp.status}: {await resp.text()}")
            return await resp.read()

    async def _list_albums_endpoint(self, endpoint: str, *, shared: bool) -> list[Album]:
        albums: list[Album] = []
        page_token: str | None = None
        while True:
            params = {"pageSize": "50"}
            if page_token:
                params["pageToken"] = page_token
            result = await self._request("GET", f"/{endpoint}", params=params)
            key = "sharedAlbums" if shared else "albums"
            albums.extend(_album_from_json(album, shared=shared) for album in result.get(key, []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return albums

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request_url(
            method, f"{GOOGLE_PHOTOS_API}{path}", params=params, json=json
        )

    async def _request_url(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = await self._token_provider.async_get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with self._session.request(
                method, url, headers=headers, params=params, json=json
            ) as resp:
                if resp.status in {401, 403}:
                    raise GooglePhotosAuthError(await resp.text())
                if resp.status >= 400:
                    raise GooglePhotosApiError(f"Google Photos {resp.status}: {await resp.text()}")
                return await resp.json()
        except aiohttp.ClientError as exc:
            raise GooglePhotosApiError(str(exc)) from exc


def _album_from_json(data: dict[str, Any], *, shared: bool) -> Album:
    count: int | None
    try:
        count = (
            int(data.get("mediaItemsCount")) if data.get("mediaItemsCount") is not None else None
        )
    except (TypeError, ValueError):
        count = None
    return Album(
        id=str(data["id"]),
        title=str(data.get("title") or data["id"]),
        media_items_count=count,
        product_url=data.get("productUrl"),
        shared=shared,
    )


def _media_item_from_json(data: dict[str, Any]) -> MediaItem:
    metadata = data.get("mediaMetadata") or {}
    return MediaItem(
        id=str(data["id"]),
        filename=str(data.get("filename") or data["id"]),
        base_url=str(data["baseUrl"]),
        mime_type=str(data.get("mimeType") or ""),
        product_url=data.get("productUrl"),
        creation_time=metadata.get("creationTime"),
        width=metadata.get("width"),
        height=metadata.get("height"),
    )
