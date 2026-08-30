from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components/google_photos_album"


def test_picker_button_notification_contains_markdown_and_raw_link():
    source = (ROOT / "button.py").read_text()

    assert "[Open Google Photos Picker]" in source
    assert "Raw link:" in source
    assert "session.picker_uri" in source
    assert "Import picked media" in source


def test_picker_session_sensor_exposes_picker_uri_attribute():
    source = (ROOT / "sensor.py").read_text()

    assert '"picker_uri"' in source
    assert "data.picker_uri" in source
    assert 'return "open" if data.picker_uri else "waiting"' in source
