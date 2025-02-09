"""Entity base class for Zavepower integration."""

import logging

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ZavepowerBaseEntity(CoordinatorEntity):
    """Common base entity for Zavepower entities, backed by a DataUpdateCoordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, system_id: str, system_name: str) -> None:
        """Initialize a base Zavepower entity."""
        super().__init__(coordinator)
        self._system_id = system_id
        self._system_name = system_name
        # Use class name + system_id to keep it unique for each entity
        self._attr_unique_id = f"{system_id}-{type(self).__name__}"

    @property
    def device_info(self):
        """Return device info to group related entities under one device."""
        return {
            "identifiers": {(DOMAIN, self._system_id)},
            "name": self._system_name,
            "manufacturer": "Zavepower",
        }

    def _get_state_data(self):
        """Return the data block for this entity's system from the coordinator."""
        if not self.coordinator.data:
            return None
        # coordinator.data is a list of dicts: [{ "system": {...}, "state": {...} }, ...]
        for entry in self.coordinator.data:
            if entry["system"]["id"] == self._system_id:
                return entry
        return None
