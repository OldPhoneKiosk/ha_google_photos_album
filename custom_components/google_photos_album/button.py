"""Button entities for Google Photos Album Picker."""

from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GooglePhotosAlbumCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up button entities."""
    coordinator: GooglePhotosAlbumCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [CreatePickerSessionButton(coordinator), ImportPickedMediaButton(coordinator)]
    )


class _BaseButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GooglePhotosAlbumCoordinator,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = ButtonEntityDescription(
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


class CreatePickerSessionButton(_BaseButton):
    """Create a Google Photos picker session."""

    def __init__(self, coordinator: GooglePhotosAlbumCoordinator) -> None:
        super().__init__(
            coordinator, "create_picker_session", "Create picker session", "mdi:image-plus"
        )

    async def async_press(self) -> None:
        session = await self.coordinator.async_create_picker_session()
        persistent_notification.async_create(
            self.coordinator.hass,
            "Open the Google Photos Picker link below, select photos, tap Done, "
            "then press **Import picked media** in Home Assistant.\n\n"
            f"[Open Google Photos Picker]({session.picker_uri})\n\n"
            f"Raw link:\n{session.picker_uri}",
            title="Google Photos Picker session",
            notification_id=f"{DOMAIN}_{self.coordinator.entry.entry_id}_picker",
        )


class ImportPickedMediaButton(_BaseButton):
    """Import picked media from the active Picker session."""

    def __init__(self, coordinator: GooglePhotosAlbumCoordinator) -> None:
        super().__init__(coordinator, "import_picked_media", "Import picked media", "mdi:download")

    async def async_press(self) -> None:
        imported = await self.coordinator.async_import_picked_media()
        message = (
            f"Imported {imported} picked image(s)."
            if imported
            else "Picker session is not ready yet, or no images were selected."
        )
        persistent_notification.async_create(
            self.coordinator.hass,
            message,
            title="Google Photos Picker import",
            notification_id=f"{DOMAIN}_{self.coordinator.entry.entry_id}_import",
        )
