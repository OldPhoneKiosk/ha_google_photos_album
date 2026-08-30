"""Google Photos Picker API REST client."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol
from uuid import uuid4

import aiohttp

from .const import GOOGLE_PICKER_API, GOOGLE_USERINFO_URL


class GooglePhotosError(Exception):
    """Base Google Photos Album error."""


class GooglePhotosAuthError(GooglePhotosError):
    """OAuth token is invalid or lacks access."""


class GooglePhotosApiError(GooglePhotosError):
    """Google Photos API request failed."""


class PickerNotReadyError(GooglePhotosError):
    """Picker session has no completed user selection yet."""


class AccessTokenProvider(Protocol):
    """Provider of valid OAuth access tokens."""

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        raise NotImplementedError


@dataclass(slots=True, frozen=True)
class PickerSession:
    """Google Photos Picker session metadata."""

    id: str
    picker_uri: str | None
    media_items_set: bool = False
    expire_time: str | None = None
    poll_interval: str | None = None
    timeout_in: str | None = None


@dataclass(slots=True, frozen=True)
class MediaItem:
    """Picked Google Photos media item metadata."""

    id: str
    filename: str
    base_url: str
    mime_type: str
    creation_time: str | None = None
    width: str | None = None
    height: str | None = None

    def to_json(self) -> dict[str, Any]:
        """Serialize to config-entry options."""
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> MediaItem:
        """Deserialize from config-entry options."""
        return cls(
            id=str(data["id"]),
            filename=str(data.get("filename") or data["id"]),
            base_url=str(data["base_url"]),
            mime_type=str(data.get("mime_type") or ""),
            creation_time=data.get("creation_time"),
            width=data.get("width"),
            height=data.get("height"),
        )


class GooglePhotosClient:
    """Small async client for Google Photos Picker API."""

    def __init__(self, session: aiohttp.ClientSession, token_provider: AccessTokenProvider) -> None:
        self._session = session
        self._token_provider = token_provider

    async def get_user_email(self) -> str:
        """Return authenticated account email."""
        data = await self._request_url("GET", GOOGLE_USERINFO_URL)
        return str(data.get("email") or "Google Photos")

    async def create_picker_session(self) -> PickerSession:
        """Create a Picker API session and return the URI for the user."""
        result = await self._request(
            "POST", "/sessions", params={"requestId": str(uuid4())}, json={}
        )
        return _picker_session_from_json(result)

    async def get_picker_session(self, session_id: str) -> PickerSession:
        """Fetch picker session state."""
        result = await self._request("GET", f"/sessions/{session_id}")
        return _picker_session_from_json(result)

    async def delete_picker_session(self, session_id: str) -> None:
        """Delete a picker session to proactively stay under resource limits."""
        await self._request("DELETE", f"/sessions/{session_id}")

    async def list_picked_media_items(self, session_id: str) -> list[MediaItem]:
        """List media items selected by the user in a completed picker session."""
        items: list[MediaItem] = []
        page_token: str | None = None
        while True:
            params: dict[str, str] = {"sessionId": session_id, "pageSize": "100"}
            if page_token:
                params["pageToken"] = page_token
            try:
                result = await self._request("GET", "/mediaItems", params=params)
            except GooglePhotosApiError as exc:
                if "FAILED_PRECONDITION" in str(exc):
                    raise PickerNotReadyError(str(exc)) from exc
                raise
            items.extend(
                _picked_media_item_from_json(item) for item in result.get("mediaItems", [])
            )
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return [item for item in items if item.mime_type.startswith("image/")]

    async def fetch_image(self, media: MediaItem, width: int = 1600, height: int = 1200) -> bytes:
        """Fetch image bytes from a Google Photos Picker media baseUrl."""
        transform = f"=w{max(width, 1)}-h{max(height, 1)}"
        async with self._session.get(f"{media.base_url}{transform}") as resp:
            if resp.status in {401, 403}:
                raise GooglePhotosAuthError(await resp.text())
            if resp.status >= 400:
                raise GooglePhotosApiError(f"Google image fetch {resp.status}: {await resp.text()}")
            return await resp.read()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request_url(
            method, f"{GOOGLE_PICKER_API}{path}", params=params, json=json
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
                if resp.status == 204:
                    return {}
                return await resp.json()
        except aiohttp.ClientError as exc:
            raise GooglePhotosApiError(str(exc)) from exc


def _picker_session_from_json(data: dict[str, Any]) -> PickerSession:
    polling = data.get("pollingConfig") or {}
    picker_uri = data.get("pickerUri")
    return PickerSession(
        id=str(data["id"]),
        picker_uri=str(picker_uri) if picker_uri else None,
        media_items_set=bool(data.get("mediaItemsSet", False)),
        expire_time=data.get("expireTime"),
        poll_interval=polling.get("pollInterval"),
        timeout_in=polling.get("timeoutIn"),
    )


def _picked_media_item_from_json(data: dict[str, Any]) -> MediaItem:
    media_file = data.get("mediaFile") or data
    metadata = media_file.get("mediaFileMetadata") or media_file.get("mediaMetadata") or {}
    return MediaItem(
        id=str(data.get("id") or media_file["baseUrl"]),
        filename=str(media_file.get("filename") or data.get("id") or "picked-media"),
        base_url=str(media_file["baseUrl"]),
        mime_type=str(media_file.get("mimeType") or ""),
        creation_time=data.get("createTime") or metadata.get("creationTime"),
        width=metadata.get("width"),
        height=metadata.get("height"),
    )
