"""Constants for the N.I.N.A. Advanced API integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "nina_api"
MANUFACTURER = "N.I.N.A. / Christian Palm (Advanced API)"

# -- Config entry defaults ----------------------------------------------
# (CONF_HOST / CONF_PORT are reused from homeassistant.const)
DEFAULT_PORT = 1888
DEFAULT_NAME = "N.I.N.A."

# -- API -----------------------------------------------------------------
API_BASE_PATH = "v2/api"
API_TIMEOUT = 10  # seconds

# Polling fallback interval; the websocket pushes updates in between.
UPDATE_INTERVAL = timedelta(seconds=30)

# Reconnect backoff for the websocket listener
WS_RECONNECT_DELAY = 5  # seconds
WS_RECONNECT_DELAY_MAX = 60  # seconds

# -- Device identifiers (sub-devices under one config entry) ------------
DEVICE_APPLICATION = "application"
DEVICE_MOUNT = "mount"
DEVICE_CAMERA = "camera"

# -- Equipment connection states as reported by NINA ---------------------
# (used to normalize the "Connected" boolean across equipment endpoints)
KEY_CONNECTED = "Connected"
