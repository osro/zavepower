"""Constants for the Zavepower integration."""

DOMAIN = "zavepower"

# API endpoints
BASE_URL = "https://app-prod-zavepower-api.azurewebsites.net/api"

LOGIN_ENDPOINT = f"{BASE_URL}/Login"
REFRESH_TOKEN_ENDPOINT = f"{BASE_URL}/RefreshToken"
USER_SYSTEMS_ENDPOINT = f"{BASE_URL}/SelectedPoolControlSystem/Get"
LATEST_STATE_ENDPOINT = f"{BASE_URL}/PoolControlSystem/GetLatestSystemState"
