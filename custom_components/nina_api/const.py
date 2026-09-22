"""Constants for the N.I.N.A. Advanced API integration."""
from __future__ import annotations

DOMAIN = "nina_api"
MANUFACTURER = "N.I.N.A. / Christian Palm (Advanced API)"

# -- Config entry defaults ----------------------------------------------
# (CONF_HOST / CONF_PORT are reused from homeassistant.const)
DEFAULT_PORT = 1888
DEFAULT_NAME = "N.I.N.A."

# -- API -----------------------------------------------------------------
API_BASE_PATH = "v2/api"
# The websocket modules are mounted next to the REST API, not under it.
WS_PATH = "v2/socket"
API_TIMEOUT = 10  # seconds

# Polling interval, adjustable per config entry via the options flow
# (CONF_SCAN_INTERVAL is reused from homeassistant.const).
DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 3600

# Read-only mode: report state, never command N.I.N.A. Set at setup and
# changeable afterwards via the options flow. Defaults to off so an existing
# entry keeps every control entity it already has.
CONF_READ_ONLY = "read_only"
DEFAULT_READ_ONLY = False

# Reconnect backoff for the websocket listener
WS_RECONNECT_DELAY = 5  # seconds
WS_RECONNECT_DELAY_MAX = 60  # seconds

# Every N.I.N.A. event is forwarded onto the Home Assistant bus under this
# single event type, with the NINA event name in the "type" field. One event
# type keeps automations simple and means events the plugin adds later work
# without a change here.
EVENT_NINA = f"{DOMAIN}_event"

# The plugin tags socket frames with this, to distinguish them from the
# envelope used by the REST API (source: HttpResponse.TypeSocket).
WS_MESSAGE_TYPE = "Socket"

# -- Device identifiers (sub-devices under one config entry) ------------
DEVICE_APPLICATION = "application"
DEVICE_MOUNT = "mount"
DEVICE_CAMERA = "camera"
DEVICE_SEQUENCE = "sequence"
# Statistics of the last saved frame. Kept apart from the camera device:
# these describe one exposure that is already on disk, not the hardware's
# current state.
DEVICE_LAST_IMAGE = "last_image"

# Display names for the devices. With has_entity_name, Home Assistant builds
# every entity_id from the device name plus the entity name, so these decide
# whether an id reads as sensor.nina_camera_temperature or the far more
# ambiguous sensor.camera_temperature. The prefix is spelled without dots on
# purpose: "N.I.N.A." slugifies to n_i_n_a.
DEVICE_NAMES = {
    DEVICE_APPLICATION: "NINA",
    DEVICE_MOUNT: "NINA Mount",
    DEVICE_CAMERA: "NINA Camera",
    DEVICE_SEQUENCE: "NINA Sequence",
    DEVICE_LAST_IMAGE: "NINA Last Image",
}

# -- Equipment connection states as reported by NINA ---------------------
# (used to normalize the "Connected" boolean across equipment endpoints)
KEY_CONNECTED = "Connected"

# -- NINA enums ----------------------------------------------------------
# The API serializes enums as integers (no JsonStringEnumConverter is
# registered), so these maps turn them back into readable states.
# Source: NINA.Equipment/Interfaces/ITelescope.cs
TRACKING_MODES: dict[int, str] = {
    0: "sidereal",
    1: "lunar",
    2: "solar",
    3: "king",
    4: "custom",
    5: "stopped",
}
TRACKING_MODE_TO_INT = {v: k for k, v in TRACKING_MODES.items()}

# Modes offered as a select; "custom" is excluded because it needs
# explicit RA/Dec rates that the select cannot supply.
TRACKING_MODE_OPTIONS = ["sidereal", "lunar", "solar", "king", "stopped"]

# Source: NINA.Core/Enum/CameraStates.cs
CAMERA_STATES: dict[int, str] = {
    -1: "no_state",
    0: "idle",
    1: "waiting",
    2: "exposing",
    3: "reading",
    4: "download",
    5: "error",
    100: "loading_file",
}

# Sequence item/trigger/condition states, already serialized as strings
# by the plugin (SequenceEntityStatus.ToString()).
SEQUENCE_STATUS_RUNNING = "RUNNING"

# -- Sequence skip targets (SequenceSkipType) ---------------------------
SKIP_CURRENT_ITEMS = "CurrentItems"
SKIP_TO_END = "ToEnd"
SKIP_TO_IMAGING = "ToImaging"

# A frame is orders of magnitude larger than any status response, and NINA
# stretches and encodes it on request, so it needs its own budget.
IMAGE_TIMEOUT = 60

# A full astro frame is many megapixels; a dashboard card shows a few
# hundred pixels. Halving it keeps the download reasonable without making
# the picture useless for a glance at framing or clouds.
IMAGE_SCALE = 0.5
