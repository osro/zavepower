"""Module contains the binary sensor entities for the Zavepower integration."""

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import ZavepowerCoordinator
from .entity import ZavepowerBaseEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Zavepower binary sensors from a config entry."""
    coordinator: ZavepowerCoordinator = hass.data[DOMAIN][entry.entry_id]

    if coordinator.data is None:
        await coordinator.async_request_refresh()

    entities = []
    for system_data in coordinator.data:
        system_id = system_data["system"]["id"]
        system_name = system_data["system"]["name"]

        entities.append(
            ZavepowerRestModeBinarySensor(coordinator, system_id, system_name)
        )
        entities.append(
            ZavepowerHighRangeBinarySensor(coordinator, system_id, system_name)
        )

        async_add_entities(entities)


class ZavepowerRestModeBinarySensor(ZavepowerBaseEntity, BinarySensorEntity):
    """Binary sensor for rest mode."""

    _attr_icon = "mdi:sleep"

    @property
    def name(self) -> str:
        """Return the display name of the binary sensor."""
        return "Rest Mode"

    @property
    def is_on(self) -> bool:
        """Return true if rest mode is on."""
        item = self._get_state_data()
        if not item or not item["state"]:
            return False
        return bool(item["state"].get("restMode", False))

    @property
    def icon(self) -> str:
        """Return device icon."""
        if self.is_on is True:
            return "mdi:sleep"
        return "mdi:sleep-off"


class ZavepowerHighRangeBinarySensor(ZavepowerBaseEntity, BinarySensorEntity):
    """Binary sensor for high range."""

    _attr_icon = "mdi:fire"

    @property
    def name(self) -> str:
        """Return the display name of the binary sensor."""
        return "High Range"

    @property
    def is_on(self) -> bool:
        """Return true if high range is on."""
        item = self._get_state_data()
        if not item or not item["state"]:
            return False
        return bool(item["state"].get("highRange", False))

    @property
    def icon(self) -> str:
        """Return device icon."""
        if self.is_on is True:
            return "mdi:fire"
        return "mdi:fire-off"
