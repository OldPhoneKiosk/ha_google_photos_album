"""Select entities for Google Photos Album Picker."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEFAULT_SELECTION_MODE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    INTERVAL_OPTIONS,
    MODE_OPTIONS,
)
from .coordinator import GooglePhotosAlbumCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up select entities."""
    coordinator: GooglePhotosAlbumCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SelectionModeSelect(coordinator), UpdateIntervalSelect(coordinator)])


class _BaseSelect(SelectEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: GooglePhotosAlbumCoordinator, key: str, name: str, icon: str
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = SelectEntityDescription(
            key=key,
            name=name,
            icon=icon,
            entity_category=EntityCategory.CONFIG,
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


class SelectionModeSelect(_BaseSelect):
    """Select random/sequential rotation."""

    def __init__(self, coordinator: GooglePhotosAlbumCoordinator) -> None:
        super().__init__(coordinator, "selection_mode", "Selection mode", "mdi:shuffle")

    @property
    def options(self) -> list[str]:
        return MODE_OPTIONS

    @property
    def current_option(self) -> str | None:
        return self.coordinator.selection_mode or DEFAULT_SELECTION_MODE

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_select_mode(option)


class UpdateIntervalSelect(_BaseSelect):
    """Select image refresh interval."""

    def __init__(self, coordinator: GooglePhotosAlbumCoordinator) -> None:
        super().__init__(coordinator, "update_interval", "Update interval", "mdi:timer-cog")

    @property
    def options(self) -> list[str]:
        return INTERVAL_OPTIONS

    @property
    def current_option(self) -> str | None:
        return self.coordinator.update_interval_option or DEFAULT_UPDATE_INTERVAL

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_select_interval(option)
