# Google Photos Album for Home Assistant

Public HACS custom integration that exposes a selected Google Photos album as a native Home Assistant `camera` entity.

This is built for OldPhoneKiosk: Home Assistant owns Google OAuth and album selection, while the phone/tablet consumes a normal HA camera/photo source and never receives Google tokens.

## Features

- Google OAuth through Home Assistant application credentials.
- Album picker as a HA `select` entity.
- Current photo as a HA `camera` entity.
- Random or sequential rotation.
- Manual/1/5/15/30/60 minute refresh interval.
- Metadata attributes/sensors for current filename and media count.
- Works as a HACS custom repository.

## Install via HACS custom repository

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=OldPhoneKiosk&repository=ha_google_photos_album&category=integration)

1. Add this repository to HACS as an integration repository.
2. Download **Google Photos Album**.
3. Restart Home Assistant.
4. Configure Google OAuth application credentials in HA if prompted.
5. Add integration: **Settings → Devices & services → Add integration → Google Photos Album**.

## Google Cloud setup

Create an OAuth client in Google Cloud:

1. Enable **Google Photos Library API**.
2. Configure OAuth consent screen.
3. Create OAuth 2.0 Client ID for a web application.
4. Add Home Assistant's OAuth redirect URI:
   `https://my.home-assistant.io/redirect/oauth`
5. Add the client ID/secret in HA application credentials when prompted.

Required scopes:

- `https://www.googleapis.com/auth/userinfo.email`
- `https://www.googleapis.com/auth/photoslibrary.readonly`

## Entities

- `camera.<account>_media` — current selected album photo.
- `select.<account>_album` — pick album.
- `select.<account>_selection_mode` — `Random` or `Sequential`.
- `select.<account>_update_interval` — `Manual`, `1 min`, `5 min`, `15 min`, `30 min`, `1 hour`.
- `sensor.<account>_media_count` — number of image items in selected album.
- `sensor.<account>_filename` — current media filename.

The camera entity includes attributes:

- `album_id`
- `album_title`
- `media_id`
- `filename`
- `product_url`
- `creation_time`
- `media_count`

## Camera service

The camera entity supports an entity service:

```yaml
service: camera.next_photo
entity_id: camera.google_photos_album_media
```

Optional mode override:

```yaml
service: camera.next_photo
entity_id: camera.google_photos_album_media
data:
  mode: Sequential
```

## Google Photos API limitation

This initial implementation uses Google Photos Library API because it is the only generally documented Google Photos API that can continuously list album media for a kiosk/photo-frame use case.

Google also documents an **Ambient API** for smart TVs/photo frames, but it is part of the Google Photos Partner Program. It is not exposed as a normal public OAuth scope in the standard authorization docs; Google says access requires first being accepted into the partner program. If OldPhoneKiosk gets Ambient API access, this integration should switch to that API behind the same HA-facing `camera`/`select` contract.

Google has changed Photos API access over time. If your OAuth project/account cannot receive the `photoslibrary.readonly` scope, this integration will fail during setup with a Google access error. Because this is our own codebase, the next controlled fallback is adding a Picker API import/cache mode without changing OldPhoneKiosk's HA-facing contract.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
python -m compileall -q custom_components/google_photos_album
pytest -q
ruff check .
```
