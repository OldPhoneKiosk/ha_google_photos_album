from __future__ import annotations

from pathlib import Path

CONFIG_FLOW = (
    Path(__file__).resolve().parents[1] / "custom_components/google_photos_album/config_flow.py"
)


def test_oauth_creation_flow_does_not_lookup_config_entry_implementation_from_flow_impl():
    """Regression: HA OAuth callback has an AuthImplementation, not a ConfigEntry.

    Newer Home Assistant versions expect async_get_config_entry_implementation(hass, entry)
    to receive a real ConfigEntry. During async_oauth_create_entry the entry does not exist yet,
    so passing self.flow_impl causes AttributeError: 'AuthImplementation' object has no attribute
    'data'. The creation flow should validate the freshly returned token directly instead.
    """
    source = CONFIG_FLOW.read_text()

    assert "async_get_config_entry_implementation(self.hass, self.flow_impl)" not in source
    assert "OAuth2Session(self.hass, data" not in source
    assert "_FlowTokenProvider(data)" in source
