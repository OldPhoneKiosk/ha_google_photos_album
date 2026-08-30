from __future__ import annotations

import pytest

from custom_components.google_photos_album.api import GooglePhotosClient
from custom_components.google_photos_album.const import ALBUM_LIBRARY


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

    def get(self, url, headers=None):
        self.calls.append({"method": "GET_IMAGE", "url": url, "headers": headers})
        response = self.responses.pop(0)
        return FakeResponse(
            response.get("payload"), response.get("status", 200), response.get("body", b"image")
        )


@pytest.mark.asyncio
async def test_list_albums_includes_library_normal_and_shared():
    session = FakeSession(
        [
            {"payload": {"albums": [{"id": "a1", "title": "Family", "mediaItemsCount": "7"}]}},
            {
                "payload": {
                    "sharedAlbums": [{"id": "s1", "title": "Shared", "mediaItemsCount": "3"}]
                }
            },
        ]
    )
    client = GooglePhotosClient(session, TokenProvider())

    albums = await client.list_albums()

    assert [album.id for album in albums] == [ALBUM_LIBRARY, "a1", "s1"]
    assert albums[1].title == "Family"
    assert albums[1].media_items_count == 7
    assert albums[2].shared is True


@pytest.mark.asyncio
async def test_album_media_search_uses_album_id_and_filters_images():
    session = FakeSession(
        [
            {
                "payload": {
                    "mediaItems": [
                        {
                            "id": "m1",
                            "filename": "one.jpg",
                            "baseUrl": "https://base/one",
                            "mimeType": "image/jpeg",
                            "mediaMetadata": {"creationTime": "2026-08-30T10:00:00Z"},
                        },
                        {
                            "id": "v1",
                            "filename": "clip.mov",
                            "baseUrl": "https://base/video",
                            "mimeType": "video/quicktime",
                        },
                    ]
                }
            }
        ]
    )
    client = GooglePhotosClient(session, TokenProvider())

    items = await client.list_media_items("album-1")

    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"].endswith("/mediaItems:search")
    assert session.calls[0]["json"] == {"albumId": "album-1", "pageSize": 100}
    assert [item.id for item in items] == ["m1"]
    assert items[0].creation_time == "2026-08-30T10:00:00Z"


@pytest.mark.asyncio
async def test_library_media_uses_media_items_get_endpoint():
    session = FakeSession([{"payload": {"mediaItems": []}}])
    client = GooglePhotosClient(session, TokenProvider())

    await client.list_media_items(ALBUM_LIBRARY)

    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"].endswith("/mediaItems")
    assert session.calls[0]["params"] == {"pageSize": "100"}


@pytest.mark.asyncio
async def test_fetch_image_adds_size_transform_and_auth_header():
    from custom_components.google_photos_album.api import MediaItem

    session = FakeSession([{"body": b"jpg-bytes"}])
    client = GooglePhotosClient(session, TokenProvider())
    media = MediaItem(
        id="m1", filename="one.jpg", base_url="https://base/one", mime_type="image/jpeg"
    )

    data = await client.fetch_image(media, width=800, height=600)

    assert data == b"jpg-bytes"
    assert session.calls[0]["url"] == "https://base/one=w800-h600"
