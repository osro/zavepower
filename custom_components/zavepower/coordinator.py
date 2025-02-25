"""Cooxrdinator for fetching data from the Zavepower API."""

import logging
from datetime import UTC, datetime, timedelta

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    LATEST_STATE_ENDPOINT,
    REFRESH_TOKEN_ENDPOINT,
    USER_SYSTEMS_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=10)

TOKEN_EXPIRATION_THRESHOLD_IN_SECONDS = 43200  # 12 hours


class ZavepowerCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from Zavepower once every 10 minutes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self._username = entry.data["username"]
        self._user_id = entry.data["user_id"]
        self._jwt_token = entry.data["jwt_token"]
        self._refresh_token = entry.data["refresh_token"]
        self._expiration = entry.data[
            "expiration"
        ]  # e.g. "2025-02-04T11:32:11.4082399Z"

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> list:
        """Fetch data from Zavepower."""
        # 1. Check if token is expired or about to expire -> Refresh if needed
        await self._ensure_valid_token()

        # 2. Get all user systems
        systems = await self._fetch_systems()

        # 3. For each system, fetch latest state
        system_states = []
        for system in systems:
            state = await self._fetch_latest_state(system["id"])
            system_states.append({"system": system, "state": state})

        return system_states

    async def _ensure_valid_token(self) -> None:
        """Refresh the token if it is expired or about to expire."""
        # Convert self._expiration to datetime
        # Example expiration format: "2025-02-04T11:32:11.4082399Z"
        expire_dt = None
        try:
            expire_dt = datetime.fromisoformat(self._expiration.replace("Z", "+00:00"))
        except ValueError:
            _LOGGER.warning(
                "Could not parse token expiration string: %s", self._expiration
            )

        now_utc = datetime.now(UTC)

        _LOGGER.debug("Expire DT: %s, Now UTC: %s", expire_dt, now_utc)

        if expire_dt is None:
            _LOGGER.debug("Expire datetime is None, refreshing token")
        elif (
            expire_dt - now_utc
        ).total_seconds() < TOKEN_EXPIRATION_THRESHOLD_IN_SECONDS:
            _LOGGER.debug(
                "Token expires in %s seconds, refreshing",
                (expire_dt - now_utc).total_seconds(),
            )
        else:
            _LOGGER.debug(
                "Token is still valid for %s seconds",
                (expire_dt - now_utc).total_seconds(),
            )

        # If we are within 12 hours of expiration, let's refresh
        if (
            expire_dt is None
            or (expire_dt - now_utc).total_seconds()
            < TOKEN_EXPIRATION_THRESHOLD_IN_SECONDS
        ):
            _LOGGER.debug("Refreshing Zavepower token")
            refreshed = await self._refresh_token_api()
            if refreshed:
                # Save updated tokens/expiration to the config entry
                data = dict(self.entry.data)
                data["jwt_token"] = self._jwt_token
                data["refresh_token"] = self._refresh_token
                data["expiration"] = self._expiration
                self.hass.config_entries.async_update_entry(self.entry, data=data)
            else:
                msg = "Could not refresh Zavepower token."
                raise UpdateFailed(msg)

    async def _refresh_token_api(self) -> bool:
        """Call the refresh token endpoint."""
        # self._refresh_token is the old refresh token to be used
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    REFRESH_TOKEN_ENDPOINT,
                    json={"refreshToken": self._refresh_token},
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "Content-Type": "application/json",
                    },
                    timeout=15,
                )
                response.raise_for_status()
                data = response.json()
                self._jwt_token = data["jwtToken"]
                self._refresh_token = data["refreshToken"]
                self._expiration = data["expiration"]
                return True
        except httpx.RequestError:
            _LOGGER.exception("Refresh token request error")
        except httpx.HTTPStatusError:
            _LOGGER.exception("Refresh token HTTP status error")
        except KeyError:
            _LOGGER.exception("Invalid response from refresh token endpoint")
        return False

    async def _fetch_systems(self) -> list:
        """Get all systems for the user."""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{USER_SYSTEMS_ENDPOINT}?userId={self._user_id}"
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Authorization": f"Bearer {self._jwt_token}",
                }
                response = await client.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                # This endpoint can return a single system or a list of systems
                data = response.json()
                # The example response is an object, but you mention
                # "There can be multiple systems"
                # So let's standardize it to a list
                if isinstance(data, dict):
                    return [data]
                if isinstance(data, list):
                    return data
                return []
        except httpx.RequestError as err:
            _LOGGER.exception("Fetch systems request error")
            msg = "Cannot fetch systems."
            raise UpdateFailed(msg) from err
        except httpx.HTTPStatusError as err:
            _LOGGER.exception("Fetch systems HTTP status error")
            msg = "Cannot fetch systems."
            raise UpdateFailed(msg) from err

    async def _fetch_latest_state(self, system_id: str) -> dict | None:
        """Get the latest system state for a given system."""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{LATEST_STATE_ENDPOINT}?id={system_id}"
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Authorization": f"Bearer {self._jwt_token}",
                }
                response = await client.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError:
            _LOGGER.exception("Fetch latest state request error")
            return None
        except httpx.HTTPStatusError:
            _LOGGER.exception("Fetch latest state HTTP status error")
            return None
