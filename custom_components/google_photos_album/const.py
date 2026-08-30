"""Constants for Google Photos Album."""

from __future__ import annotations

DOMAIN = "google_photos_album"
PLATFORMS = ["camera", "button", "select", "sensor"]

MANUFACTURER = "Google Photos"

CONF_SELECTION_MODE = "selection_mode"
CONF_UPDATE_INTERVAL = "update_interval"

CONF_PICKER_SESSION_ID = "picker_session_id"
CONF_PICKER_URI = "picker_uri"
CONF_PICKER_EXPIRE_TIME = "picker_expire_time"
CONF_PICKED_MEDIA = "picked_media"

MODE_RANDOM = "Random"
MODE_SEQUENTIAL = "Sequential"
MODE_OPTIONS = [MODE_RANDOM, MODE_SEQUENTIAL]
DEFAULT_SELECTION_MODE = MODE_RANDOM

INTERVAL_MANUAL = "Manual"
INTERVAL_15_SEC = "15s"
INTERVAL_30_SEC = "30s"
INTERVAL_60_SEC = "60s"
INTERVAL_120_SEC = "120s"
INTERVAL_5_MIN = "5min"
INTERVAL_OPTIONS = [
    INTERVAL_MANUAL,
    INTERVAL_15_SEC,
    INTERVAL_30_SEC,
    INTERVAL_60_SEC,
    INTERVAL_120_SEC,
    INTERVAL_5_MIN,
]
INTERVAL_SECONDS = {
    INTERVAL_MANUAL: None,
    INTERVAL_15_SEC: 15,
    INTERVAL_30_SEC: 30,
    INTERVAL_60_SEC: 60,
    INTERVAL_120_SEC: 120,
    INTERVAL_5_MIN: 300,
    # Backward-compatible values that may already be persisted in options.
    "1 min": 60,
    "2 min": 120,
    "5 min": 300,
    "15 min": 900,
    "30 min": 1800,
    "1 hour": 3600,
}
DEFAULT_UPDATE_INTERVAL = INTERVAL_60_SEC

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
]

GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_PICKER_API = "https://photospicker.googleapis.com/v1"
