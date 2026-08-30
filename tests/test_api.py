from __future__ import annotations

import pytest

from custom_components.google_photos_album.api import (
    GooglePhotosClient,
    MediaItem,
    PickerNotReadyError,
)
from custom_components.google_photos_album.const import GOOGLE_PICKER_API


class TokenProvider:
    async def async_get_access_token(self) -> str:
        return "token-1"


class FakeResponse:
    def __init__(self, payload=None, status=200, body=b"image"):
        self.payload = payload if payload is not None else {}
        self.status = status
        self.body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self.payload

    async def text(self):
        return str(self.payload)

    async def read(self):
        return self.body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers=None, params=None, json=None):
        self.calls.append(
            {"method": method, "url": url, "headers": headers, "params": params, "json": json}
        )
        response = self.responses.pop(0)
        return FakeResponse(
            response.get("payload"), response.get("status", 200), response.get("body", b"")
        )

    def get(self, url):
        self.calls.append({"method": "GET_IMAGE", "url": url})
        response = self.responses.pop(0)
        return FakeResponse(
            response.get("payload"), response.get("status", 200), response.get("body", b"image")
        )


@pytest.mark.asyncio
async def test_create_picker_session_posts_request_id_and_returns_uri():
    session = FakeSession(
        [
            {
                "payload": {
                    "id": "sess-1",
                    "pickerUri": "https://photos.google.com/picker/sess-1",
                    "mediaItemsSet": False,
                    "expireTime": "2026-08-30T10:00:00Z",
                    "pollingConfig": {"pollInterval": "5s", "timeoutIn": "600s"},
                }
            }
        ]
    )
    client = GooglePhotosClient(session, TokenProvider())

    picker = await client.create_picker_session()

    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == f"{GOOGLE_PICKER_API}/sessions"
    assert "requestId" in session.calls[0]["params"]
    assert session.calls[0]["json"] == {}
    assert picker.id == "sess-1"
    assert picker.picker_uri.endswith("sess-1")
    assert picker.poll_interval == "5s"


@pytest.mark.asyncio
async def test_get_picker_session_reads_media_items_set():
    session = FakeSession(
        [
            {
                "payload": {
                    "id": "sess-1",
                    "pickerUri": "https://photos.google.com/picker/sess-1",
                    "mediaItemsSet": True,
                }
            }
        ]
    )
    client = GooglePhotosClient(session, TokenProvider())

    picker = await client.get_picker_session("sess-1")

    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"] == f"{GOOGLE_PICKER_API}/sessions/sess-1"
    assert picker.media_items_set is True


@pytest.mark.asyncio
async def test_list_picked_media_items_uses_session_id_and_filters_images():
    session = FakeSession(
        [
            {
                "payload": {
                    "mediaItems": [
                        {
                            "id": "m1",
                            "createTime": "2026-08-30T10:00:00Z",
                            "mediaFile": {
                                "filename": "one.jpg",
                                "baseUrl": "https://base/one",
                                "mimeType": "image/jpeg",
                                "mediaFileMetadata": {"width": "4000", "height": "3000"},
                            },
                        },
                        {
                            "id": "v1",
                            "mediaFile": {
                                "filename": "clip.mov",
                                "baseUrl": "https://base/video",
                                "mimeType": "video/quicktime",
                            },
                        },
                    ]
                }
            }
        ]
    )
    client = GooglePhotosClient(session, TokenProvider())

    items = await client.list_picked_media_items("sess-1")

    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"] == f"{GOOGLE_PICKER_API}/mediaItems"
    assert session.calls[0]["params"] == {"sessionId": "sess-1", "pageSize": "100"}
    assert [item.id for item in items] == ["m1"]
    assert items[0].filename == "one.jpg"
    assert items[0].creation_time == "2026-08-30T10:00:00Z"
    assert items[0].width == "4000"


@pytest.mark.asyncio
async def test_list_picked_media_items_raises_not_ready_on_failed_precondition():
    session = FakeSession(
        [{"payload": {"error": {"status": "FAILED_PRECONDITION"}}, "status": 400}]
    )
    client = GooglePhotosClient(session, TokenProvider())

    with pytest.raises(PickerNotReadyError):
        await client.list_picked_media_items("sess-1")


@pytest.mark.asyncio
async def test_fetch_image_adds_size_transform():
    session = FakeSession([{"body": b"jpg-bytes"}])
    client = GooglePhotosClient(session, TokenProvider())
    media = MediaItem(
        id="m1", filename="one.jpg", base_url="https://base/one", mime_type="image/jpeg"
    )

    data = await client.fetch_image(media, width=800, height=600)

    assert data == b"jpg-bytes"
    assert session.calls[0]["url"] == "https://base/one=w800-h600"
