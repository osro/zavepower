"""Coordinator for fetching data from the Zavepower API."""

import logging
from datetime import UTC, datetime, timedelta

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    LATEST_STATE_ENDPOINT,
    LOGIN_ENDPOINT,
    REFRESH_TOKEN_ENDPOINT,
    USER_SYSTEMS_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=10)
HTTP_TIMEOUT = 30  # Increased from 15 to 30 seconds for better reliability
MAX_RETRIES = 3  # Number of retry attempts for API calls
CONSECUTIVE_FAILURES_THRESHOLD = 2  # Number of failures before forcing token refresh

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
        self._consecutive_failures = 0  # Counter for consecutive failures

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> list:
        """Fetch data from Zavepower."""
        try:
            # 1. Check if token is expired or about to expire -> Refresh if needed
            await self._ensure_valid_token()

            # 2. Get all user systems
            systems = await self._fetch_systems()

            # 3. For each system, fetch latest state
            system_states = []
            for system in systems:
                state = await self._fetch_latest_state(system["id"])
                system_states.append({"system": system, "state": state})

            # Reset failure counter on success
            self._consecutive_failures = 0
        except (UpdateFailed, httpx.RequestError, httpx.HTTPStatusError) as err:
            self._consecutive_failures += 1
            _LOGGER.exception(
                "Error updating Zavepower data (attempt %s)",
                self._consecutive_failures,
            )

            # If we have multiple consecutive failures, try a forced token refresh
            if self._consecutive_failures >= CONSECUTIVE_FAILURES_THRESHOLD:
                _LOGGER.warning(
                    "Multiple consecutive update failures, forcing token refresh"
                )
                try:
                    await self._login_api()
                    # Save updated tokens to config entry
                    data = dict(self.entry.data)
                    data["jwt_token"] = self._jwt_token
                    data["refresh_token"] = self._refresh_token
                    data["expiration"] = self._expiration
                    self.hass.config_entries.async_update_entry(self.entry, data=data)
                except (
                    httpx.RequestError,
                    httpx.HTTPStatusError,
                    KeyError,
                ):
                    _LOGGER.exception("Forced login attempt failed")

            error_msg = "Failed to update data"
            raise UpdateFailed(error_msg) from err
        else:
            return system_states

    async def _ensure_valid_token(self) -> bool:
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

        # Force refresh if we couldn't parse expiration or it's within threshold
        needs_refresh = expire_dt is None
        if expire_dt is not None:
            time_remaining = (expire_dt - now_utc).total_seconds()
            needs_refresh = time_remaining < TOKEN_EXPIRATION_THRESHOLD_IN_SECONDS

            if needs_refresh:
                _LOGGER.debug("Token expires in %s seconds, refreshing", time_remaining)
            else:
                _LOGGER.debug("Token is still valid for %s seconds", time_remaining)

        # If we need to refresh, do so
        if needs_refresh:
            _LOGGER.debug("Refreshing Zavepower token")
            try:
                refreshed = await self._refresh_token_api()
            except Exception:
                _LOGGER.exception("Error refreshing token")
                return False
            else:
                if refreshed:
                    # Save updated tokens/expiration to the config entry
                    data = dict(self.entry.data)
                    data["jwt_token"] = self._jwt_token
                    data["refresh_token"] = self._refresh_token
                    data["expiration"] = self._expiration
                    self.hass.config_entries.async_update_entry(self.entry, data=data)
                    return True

                _LOGGER.error("Failed to refresh token")
                return False

        return True  # Token is valid

    async def _refresh_token_api(self) -> bool:
        """Call the refresh token endpoint."""
        # self._refresh_token is the old refresh token to be used
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        REFRESH_TOKEN_ENDPOINT,
                        json={"refreshToken": self._refresh_token},
                        headers={
                            "Accept": "application/json, text/plain, */*",
                            "Content-Type": "application/json",
                        },
                        timeout=HTTP_TIMEOUT,
                    )
                    response.raise_for_status()
                    data = response.json()
                    self._jwt_token = data["jwtToken"]
                    self._refresh_token = data["refreshToken"]
                    self._expiration = data["expiration"]
                    return True
            except (httpx.RequestError, httpx.HTTPStatusError) as err:
                _LOGGER.warning(
                    "Refresh token attempt %s/%s failed: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    str(err),
                )
                await self.hass.async_add_executor_job(
                    lambda: __import__("time").sleep(2)
                )
            except KeyError as err:
                _LOGGER.warning("Invalid response from refresh token endpoint: %s", err)
                break  # Don't retry on invalid response format

        _LOGGER.warning("All refresh token attempts failed, trying login endpoint")
        return await self._login_api()

    async def _login_api(self) -> bool:
        """Call the login endpoint as a fallback when refresh token fails."""
        # Get password from entry secrets
        password = self.entry.data.get("password")
        if not password:
            _LOGGER.error(
                "No password stored in config entry, can't use login endpoint"
            )
            return False

        for attempt in range(MAX_RETRIES):
            try:
                _LOGGER.debug(
                    "Attempting direct login with credentials, attempt %s/%s",
                    attempt + 1,
                    MAX_RETRIES,
                )
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        LOGIN_ENDPOINT,
                        json={
                            "username": self._username,
                            "password": password,
                        },
                        timeout=HTTP_TIMEOUT,
                    )
                    response.raise_for_status()
                    data = response.json()

                    if "jwtToken" not in data or "refreshToken" not in data:
                        _LOGGER.error("Invalid response from login endpoint")
                        return False

                    self._jwt_token = data["jwtToken"]
                    self._refresh_token = data["refreshToken"]
                    self._expiration = data["expiration"]
                    _LOGGER.info("Successfully logged in with username/password")
                    return True
            except httpx.RequestError as err:
                _LOGGER.warning(
                    "Login attempt %s/%s request error: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    str(err),
                )
                await self.hass.async_add_executor_job(
                    lambda: __import__("time").sleep(2)
                )
            except httpx.HTTPStatusError as err:
                _LOGGER.warning(
                    "Login attempt %s/%s HTTP status error: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    str(err),
                )
                await self.hass.async_add_executor_job(
                    lambda: __import__("time").sleep(2)
                )
            except KeyError:
                _LOGGER.exception("Invalid response from login endpoint")
                break  # Don't retry on invalid response format

        _LOGGER.error("All login attempts failed")
        return False

    async def _handle_auth_error(
        self, attempt: int, *, token_refreshed: bool
    ) -> tuple[bool, bool]:
        """
        Handle 401/403 authentication errors with token refresh or login.

        Returns:
            tuple: (continue_immediately, token_refreshed)

        """
        if token_refreshed and attempt < MAX_RETRIES - 1:
            # If we've already refreshed the token and still get 401,
            # try to log in
            _LOGGER.warning("Still unauthorized after token refresh, trying full login")
            if await self._login_api():
                # Save updated tokens to config entry
                data = dict(self.entry.data)
                data["jwt_token"] = self._jwt_token
                data["refresh_token"] = self._refresh_token
                data["expiration"] = self._expiration
                self.hass.config_entries.async_update_entry(self.entry, data=data)
                return True, token_refreshed  # Continue immediately with new token
        elif attempt < MAX_RETRIES - 1:
            _LOGGER.info("Unauthorized error, refreshing token")
            if await self._ensure_valid_token():
                # Token refreshed successfully
                return True, True  # Continue immediately with token_refreshed=True

        return False, token_refreshed

    async def _fetch_systems(self) -> list:
        """Get all systems for the user."""
        token_refreshed = False  # Track if we've already tried refreshing the token

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    url = f"{USER_SYSTEMS_ENDPOINT}?userId={self._user_id}"
                    headers = {
                        "Accept": "application/json, text/plain, */*",
                        "Authorization": f"Bearer {self._jwt_token}",
                    }
                    response = await client.get(
                        url, headers=headers, timeout=HTTP_TIMEOUT
                    )
                    response.raise_for_status()
                    # This endpoint can return a single system or a list of systems
                    data = response.json()
                    # Standardize response to a list
                    if isinstance(data, dict):
                        return [data]
                    if isinstance(data, list):
                        return data
                    return []
            except httpx.RequestError as err:
                _LOGGER.warning(
                    "Fetch systems attempt %s/%s request error: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    str(err),
                )
                if attempt < MAX_RETRIES - 1:
                    await self.hass.async_add_executor_job(
                        lambda: __import__("time").sleep(2)
                    )
                else:
                    msg = "Cannot fetch systems after multiple attempts"
                    raise UpdateFailed(msg) from err
            except httpx.HTTPStatusError as err:
                response = getattr(err, "response", None)
                _LOGGER.warning(
                    "Fetch systems attempt %s/%s HTTP status error: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    str(err),
                )
                # If we get an unauthorized error, try to refresh the token
                if response and response.status_code in (401, 403):
                    (
                        continue_immediately,
                        token_refreshed,
                    ) = await self._handle_auth_error(
                        attempt, token_refreshed=token_refreshed
                    )
                    if continue_immediately:
                        continue

                if attempt < MAX_RETRIES - 1:
                    await self.hass.async_add_executor_job(
                        lambda: __import__("time").sleep(2)
                    )

        msg = "Maximum retries reached while trying to fetch systems"
        raise UpdateFailed(msg)

    async def _fetch_latest_state(self, system_id: str) -> dict | None:
        """Get the latest system state for a given system."""
        token_refreshed = False  # Track if we've already tried refreshing the token

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    url = f"{LATEST_STATE_ENDPOINT}?id={system_id}"
                    headers = {
                        "Accept": "application/json, text/plain, */*",
                        "Authorization": f"Bearer {self._jwt_token}",
                    }
                    response = await client.get(
                        url, headers=headers, timeout=HTTP_TIMEOUT
                    )
                    response.raise_for_status()
                    return response.json()
            except httpx.RequestError as err:
                _LOGGER.warning(
                    "Fetch latest state attempt %s/%s request error for system %s: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    system_id,
                    str(err),
                )
                if attempt < MAX_RETRIES - 1:
                    await self.hass.async_add_executor_job(
                        lambda: __import__("time").sleep(1)
                    )
            except httpx.HTTPStatusError as err:
                response = getattr(err, "response", None)
                _LOGGER.warning(
                    "Fetch latest state attempt %s/%s HTTP status error"
                    " for system %s: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    system_id,
                    str(err),
                )
                # If we get an unauthorized error, try to refresh the token
                if response and response.status_code in (401, 403):
                    (
                        continue_immediately,
                        token_refreshed,
                    ) = await self._handle_auth_error(
                        attempt, token_refreshed=token_refreshed
                    )
                    if continue_immediately:
                        continue

                if attempt < MAX_RETRIES - 1:
                    await self.hass.async_add_executor_job(
                        lambda: __import__("time").sleep(1)
                    )

        _LOGGER.error(
            "Could not fetch latest state for system %s after %s attempts",
            system_id,
            MAX_RETRIES,
        )
        return None
