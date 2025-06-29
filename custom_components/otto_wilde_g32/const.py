"""Constants for the Otto Wilde G32 Grill integration."""
from homeassistant.const import Platform

DOMAIN = "otto_wilde_g32"

# Add TEXT to the list of platforms
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]

# API Endpoints
API_BASE_URL = "https://mobile-api.ottowildeapp.com"
LOGIN_ENDPOINT = f"{API_BASE_URL}/login"
GRILLS_ENDPOINT = f"{API_BASE_URL}/v2/grills"

# TCP Socket connection details
TCP_HOST = "socket.ottowildeapp.com"
TCP_PORT = 4502

