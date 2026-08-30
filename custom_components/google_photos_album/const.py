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
INTERVAL_1_MIN = "1 min"
INTERVAL_5_MIN = "5 min"
INTERVAL_15_MIN = "15 min"
INTERVAL_30_MIN = "30 min"
INTERVAL_1_HOUR = "1 hour"
INTERVAL_OPTIONS = [
    INTERVAL_MANUAL,
    INTERVAL_1_MIN,
    INTERVAL_5_MIN,
    INTERVAL_15_MIN,
    INTERVAL_30_MIN,
    INTERVAL_1_HOUR,
]
INTERVAL_SECONDS = {
    INTERVAL_MANUAL: None,
    INTERVAL_1_MIN: 60,
    INTERVAL_5_MIN: 300,
    INTERVAL_15_MIN: 900,
    INTERVAL_30_MIN: 1800,
    INTERVAL_1_HOUR: 3600,
}
DEFAULT_UPDATE_INTERVAL = INTERVAL_15_MIN

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
]

GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_PICKER_API = "https://photospicker.googleapis.com/v1"
