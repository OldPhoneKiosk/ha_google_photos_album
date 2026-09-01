# Changelog

## 1.1.0 - 2026-09-01

- Polish the public HACS/GitHub presentation: repository topics, homepage, description, README badges and install guidance, and stable release metadata.
- Declare the integration as a Home Assistant service integration and keep official Google Photos branding visible in README/HACS assets.

## 1.0.0 - 2026-09-01

- Mark Google Photos Album as the first stable HACS release.
- Keep HACS metadata configured for release/tag source downloads.
- Add official Google Photos branding icons for HACS/README display.

## 0.2.7 - 2026-08-30

- Change Google Photos Picker update interval options to photo-frame-friendly values: `15s`, `30s`, `60s`, `120s`, and `5min`.
- Make `Import picked media` replace the previous picked-media set and delete stale cached files instead of appending to the old selection.
- Keep support for previously persisted interval values so existing configs do not break after upgrade.

## 0.2.6 - 2026-08-30

- Cache imported Google Photos Picker images to local HA storage at import time so the camera no longer depends on expiring Picker `baseUrl` values.
- Prefer cached image bytes when serving the HA camera; backfill cache on camera reads when possible.

## 0.2.5 - 2026-08-30

- Fetch Google Photos Picker media bytes with the OAuth bearer token so HA camera snapshots render in dashboard cards and OldPhoneKiosk Photos screen.
- Treat empty Google image responses as explicit camera fetch errors instead of silently returning blank images.

## 0.2.4 - 2026-08-30

- Fix `Import picked media` when Google Picker session polling omits `pickerUri`; the integration now keeps the persisted picker link and imports selected media normally.

## 0.2.3 - 2026-08-30

- Fix Picker button notifications on newer Home Assistant by using the public persistent_notification helper instead of `hass.components`.

## 0.2.2 - 2026-08-30

- Make Google Photos Picker sessions easier to open from Home Assistant by using a markdown link in the persistent notification and an explicit `open` picker-session sensor state with `picker_uri` attribute.

## 0.2.1 - 2026-08-30

- Fix Google OAuth callback validation on newer Home Assistant versions by avoiding ConfigEntry OAuth helpers before the entry exists.

## 0.2.0 - 2026-08-30

- Switch the backend from restricted Library API album listing to official Google Photos Picker API.
- Use `photospicker.mediaitems.readonly` instead of `photoslibrary.readonly`.
- Add Picker session creation/import workflow with HA button entities and diagnostic picker session sensor.
- Store imported picked media in config-entry options and rotate them through the existing camera entity.

## 0.1.0 - 2026-08-30

- Initial public HACS integration.
- Google OAuth via Home Assistant application credentials.
- Expose a selected Google Photos album as a native HA camera entity.
- Add album, selection mode, and update interval select entities.
