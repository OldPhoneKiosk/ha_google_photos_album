# Google Photos Album for Home Assistant

Public HACS custom integration that exposes media selected with the official Google Photos **Picker API** as a native Home Assistant `camera` entity.

This is built for OldPhoneKiosk: Home Assistant owns Google OAuth and selected-photo cache, while the phone/tablet consumes a normal HA camera/photo source and never receives Google tokens.

## Why Picker API

Google's broad Library API scopes for reading a user's existing library/albums were restricted after March 31, 2025. The official public replacement for selecting user-library media is the Picker API with:

```text
https://www.googleapis.com/auth/photospicker.mediaitems.readonly
```

Google also documents an Ambient API for smart TVs/photo frames, but that requires acceptance into the Google Photos Partner Program. Picker API is the public, non-partner path.

## Features

- Google OAuth through Home Assistant application credentials.
- Creates a Google Photos Picker session from HA.
- Shows the `pickerUri` in a persistent notification and a diagnostic sensor attribute.
- Imports user-selected photos after the user taps Done in Google Photos.
- Current selected/cached photo as a HA `camera` entity.
- Random or sequential rotation.
- Manual/1/5/15/30/60 minute refresh interval.
- Metadata sensors for current filename, media count, and picker session state.
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

1. Enable **Google Photos Picker API**.
2. Configure OAuth consent screen.
3. Create OAuth 2.0 Client ID for a web application.
4. Add Home Assistant's OAuth redirect URI:
   `https://my.home-assistant.io/redirect/oauth`
5. Add the client ID/secret in HA application credentials when prompted.

Required scopes:

- `https://www.googleapis.com/auth/userinfo.email`
- `https://www.googleapis.com/auth/photospicker.mediaitems.readonly`

## Entities

- `camera.<account>_media` — current cached/selected photo.
- `button.<account>_create_picker_session` — create a Google Photos Picker session.
- `button.<account>_import_picked_media` — import selected photos after the user taps Done.
- `select.<account>_selection_mode` — `Random` or `Sequential`.
- `select.<account>_update_interval` — `Manual`, `1 min`, `5 min`, `15 min`, `30 min`, `1 hour`.
- `sensor.<account>_media_count` — number of cached picked image items.
- `sensor.<account>_filename` — current media filename.
- `sensor.<account>_picker_session` — `none`, `waiting`, or `ready`; attributes include `picker_uri`.

## Usage flow

1. Press **Create picker session** in HA.
2. Open the Google Photos URL from the persistent notification or `sensor.*_picker_session` attribute `picker_uri`.
3. Select photos/videos in Google Photos and tap **Done**.
4. Press **Import picked media** in HA.
5. Use the `camera.*_media` entity as OldPhoneKiosk's photo source.

Picker API is selection/import based. It does not continuously sync an existing Google Photos album. To add new photos later, create another picker session and import again.

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

## Ambient API future backend

Google's Ambient API is the better direct fit for smart TVs/photo frames, but it is part of the Google Photos Partner Program. If OldPhoneKiosk gets Ambient API access, this integration can add that backend behind the same HA-facing `camera`/`select` contract.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
python -m compileall -q custom_components/google_photos_album
pytest -q
ruff check .
```
