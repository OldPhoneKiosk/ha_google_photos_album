"""Sensor entities for Google Photos Album."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GooglePhotosAlbumCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up metadata sensors."""
    coordinator: GooglePhotosAlbumCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MediaCountSensor(coordinator), CurrentFilenameSensor(coordinator)])


class _BaseSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GooglePhotosAlbumCoordinator,
        key: str,
        name: str,
        icon: str,
        category: EntityCategory | None = None,
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = SensorEntityDescription(
            key=key,
            name=name,
            icon=icon,
            entity_category=category,
        )
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_coordinator_update))
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class MediaCountSensor(_BaseSensor):
    """Number of photos available in selected album."""

    def __init__(self, coordinator: GooglePhotosAlbumCoordinator) -> None:
        super().__init__(
            coordinator, "media_count", "Media count", "mdi:counter", EntityCategory.DIAGNOSTIC
        )

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.media_items) if self.coordinator.data else 0


class CurrentFilenameSensor(_BaseSensor):
    """Filename of current selected photo."""

    def __init__(self, coordinator: GooglePhotosAlbumCoordinator) -> None:
        super().__init__(
            coordinator, "filename", "Filename", "mdi:file-image", EntityCategory.DIAGNOSTIC
        )

    @property
    def native_value(self) -> str | None:
        media = self.coordinator.data.current_media if self.coordinator.data else None
        return media.filename if media else None
