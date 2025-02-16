"""Zavepower sensor integration for Home Assistant."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import ZavepowerBaseEntity

if TYPE_CHECKING:
    from .coordinator import ZavepowerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Zavepower sensors from a config entry."""
    coordinator: ZavepowerCoordinator = hass.data[DOMAIN][entry.entry_id]

    if coordinator.data is None:
        await coordinator.async_request_refresh()

    entities = []
    # coordinator.data is a list of dicts: [{ "system": {...}, "state": {...} }, ...]
    for system_data in coordinator.data:
        system_id = system_data["system"]["id"]
        system_name = system_data["system"]["name"]

        entities.append(ZavepowerCurrentTempSensor(coordinator, system_id, system_name))
        entities.append(ZavepowerSetTempSensor(coordinator, system_id, system_name))

    async_add_entities(entities)


class ZavepowerCurrentTempSensor(ZavepowerBaseEntity, SensorEntity):
    """Sensor for current temperature."""

    _attr_icon = "mdi:pool-thermometer"

    @property
    def name(self) -> str:
        """Return the display name of the sensor."""
        return "Current Temperature"

    @property
    def native_value(self) -> float | None:
        """Return the current water temperature from the system state."""
        item = self._get_state_data()
        if item and item["state"]:
            return item["state"].get("currentTemperature")
        return None

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "°C"


class ZavepowerSetTempSensor(ZavepowerBaseEntity, SensorEntity):
    """Sensor for set temperature."""

    _attr_icon = "mdi:target"

    @property
    def name(self) -> str:
        """Return the display name of the sensor."""
        return "Set Temperature"

    @property
    def native_value(self) -> float | None:
        """Return the set (target) water temperature from the system state."""
        item = self._get_state_data()
        if item and item["state"]:
            return item["state"].get("setTemperature")
        return None

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "°C"
