# Changelog

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
