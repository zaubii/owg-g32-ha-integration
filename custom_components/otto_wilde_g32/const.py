"""Constants for the Otto Wilde G32 Grill integration."""
from homeassistant.const import Platform

DOMAIN = "otto_wilde_g32"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]

# Configuration constants
CONF_DEVICE_TRACKER = "device_tracker"

# API Endpoints
API_BASE_URL = "https://mobile-api.ottowildeapp.com"
LOGIN_ENDPOINT = f"{API_BASE_URL}/login"
GRILLS_ENDPOINT = f"{API_BASE_URL}/v2/grills"

# TCP Socket connection details
TCP_HOST = "socket.ottowildeapp.com"
TCP_PORT = 4502

# Connection retry logic constants
HEARTBEAT_TIMEOUT_SECONDS = 90
RAPID_RETRY_ATTEMPTS = 5
RAPID_RETRY_DELAY_SECONDS = 2
INITIAL_RETRY_DELAY_SECONDS = 30
MAX_RETRY_DELAY_SECONDS = 300  # 5 minutes
OVERALL_TIMEOUT_MINUTES = 30
