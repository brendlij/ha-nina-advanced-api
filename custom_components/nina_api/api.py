"""Thin async client for the N.I.N.A. Advanced API.

This module has no Home Assistant imports so it can be unit tested in
isolation and reused outside of HA if needed.

API reference: https://bump.sh/christian-photo/doc/advanced-api/
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE_PATH, API_TIMEOUT, WS_PATH

_LOGGER = logging.getLogger(__name__)


def _bool(value: bool) -> str:
    """Render a Python bool the way the API's query parser expects it.

    aiohttp would serialize True as "True", which EmbedIO does not parse
    as a boolean.
    """
    return "true" if value else "false"


class NinaApiError(Exception):
    """Raised for any transport-level or unexpected-shape error."""


class NinaApiConnectionError(NinaApiError):
    """Raised when the NINA instance cannot be reached."""


class NinaApiNotFoundError(NinaApiError):
    """Raised when something answers on host:port but isn't the Advanced API.

    A 404 on a known-good endpoint means we're talking to some other web
    server (or a NINA API version that predates the endpoint), which is a
    very different problem from "nothing is listening".
    """


class NinaApiResponseError(NinaApiError):
    """Raised when NINA responds but reports an application-level error.

    NINA's Advanced API wraps every response as:
        {"Response": ..., "Error": "", "StatusCode": 200, "Success": true, "Type": "..."}
    Success == false with a populated Error is surfaced here.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NinaApiClient:
    """Client for the N.I.N.A. Advanced API (v2)."""

    def __init__(
        self,
        host: str,
        port: int,
        session: aiohttp.ClientSession,
    ) -> None:
        self._host = host
        self._port = port
        self._session = session

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._port}/{API_BASE_PATH}"

    @property
    def websocket_url(self) -> str:
        # The socket module is mounted at /v2/socket, *not* under /v2/api.
        return f"ws://{self._host}:{self._port}/{WS_PATH}"

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Perform a request and unwrap NINA's standard envelope."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        _LOGGER.debug("NINA request: %s %s params=%s", method, url, params)
        try:
            async with self._session.request(
                method,
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            ) as resp:
                # The Advanced API always answers HTTP 200 and signals
                # application errors inside the envelope, so any non-200 here
                # means we are not talking to the API we think we are.
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except aiohttp.ClientResponseError as err:
            if err.status == 404:
                raise NinaApiNotFoundError(
                    f"{url} returned 404 - host:port does not look like the "
                    "N.I.N.A. Advanced API"
                ) from err
            raise NinaApiError(f"HTTP {err.status} from NINA for {url}") from err
        except aiohttp.ClientConnectionError as err:
            raise NinaApiConnectionError(
                f"Cannot connect to NINA at {self._host}:{self._port}: {err}"
            ) from err
        except TimeoutError as err:
            raise NinaApiConnectionError(
                f"Timeout connecting to NINA at {self._host}:{self._port}"
            ) from err
        except aiohttp.ClientError as err:
            raise NinaApiConnectionError(
                f"Transport error talking to NINA at {self._host}:{self._port}: {err}"
            ) from err
        except ValueError as err:
            raise NinaApiError(f"Invalid JSON response from NINA for {url}") from err

        if not isinstance(data, dict):
            raise NinaApiError(f"Unexpected response shape from NINA: {data!r}")

        if data.get("Success") is False:
            raise NinaApiResponseError(
                data.get("Error") or "Unknown NINA API error",
                status_code=data.get("StatusCode"),
            )

        return data.get("Response")

    # -- Application / connection status ---------------------------------

    async def get_api_version(self) -> Any:
        """Return the Advanced API plugin version.

        This is the cheapest endpoint that exists on every build, so it is
        the reachability probe used by config_flow and the coordinator.
        """
        return await self._request("GET", "version")

    async def get_nina_version(self, friendly: bool = True) -> Any:
        """Return the N.I.N.A. version string itself."""
        return await self._request(
            "GET", "version/nina", params={"friendly": _bool(friendly)}
        )

    async def get_equipment_info(self) -> Any:
        """Return connection state for every device in one call."""
        return await self._request("GET", "equipment/info")

    async def get_time(self) -> Any:
        """Return the local time of the machine running NINA."""
        return await self._request("GET", "time")

    async def get_application_start(self) -> Any:
        """Return the timestamp NINA was started at."""
        return await self._request("GET", "application-start")

    async def get_plugins(self) -> Any:
        """Return the list of installed NINA plugins."""
        return await self._request("GET", "application/plugins")

    async def get_active_tab(self) -> Any:
        """Return the tab currently open in the NINA UI."""
        return await self._request("GET", "application/get-tab")

    async def switch_tab(self, tab: str) -> Any:
        """Switch the NINA UI to `tab` (e.g. 'imaging', 'equipment')."""
        return await self._request(
            "GET", "application/switch-tab", params={"tab": tab}
        )

    async def get_image_history(self, count_only: bool = False) -> Any:
        """Return the image history of the current session."""
        return await self._request(
            "GET",
            "image-history",
            params={"all": _bool(not count_only), "count": _bool(count_only)},
        )

    # -- Mount -------------------------------------------------------------

    async def get_mount_info(self) -> Any:
        return await self._request("GET", "equipment/mount/info")

    async def mount_connect(self) -> Any:
        return await self._request("GET", "equipment/mount/connect")

    async def mount_disconnect(self) -> Any:
        return await self._request("GET", "equipment/mount/disconnect")

    async def mount_park(self) -> Any:
        return await self._request("GET", "equipment/mount/park")

    async def mount_unpark(self) -> Any:
        return await self._request("GET", "equipment/mount/unpark")

    async def mount_home(self) -> Any:
        return await self._request("GET", "equipment/mount/home")

    async def mount_set_tracking(self, tracking_mode: int) -> Any:
        """tracking_mode: NINA TrackingMode enum.

        0=Sidereal, 1=Lunar, 2=Solar, 3=King, 4=Custom, 5=Stopped.
        """
        return await self._request(
            "GET", "equipment/mount/tracking", params={"mode": tracking_mode}
        )

    async def mount_flip(self) -> Any:
        """Trigger a meridian flip."""
        return await self._request("GET", "equipment/mount/flip")

    async def mount_slew(
        self,
        ra: float,
        dec: float,
        wait_for_result: bool = False,
        center: bool = False,
        rotate: bool = False,
        rotation_angle: float = 0,
    ) -> Any:
        """Slew to RA/Dec (both in degrees).

        `center` plate-solves and centers after the slew; `rotate` also
        matches the rotator to `rotation_angle`.
        """
        return await self._request(
            "GET",
            "equipment/mount/slew",
            params={
                "ra": ra,
                "dec": dec,
                "waitForResult": _bool(wait_for_result),
                "center": _bool(center),
                "rotate": _bool(rotate),
                "rotationAngle": rotation_angle,
            },
        )

    async def mount_stop_slew(self) -> Any:
        """Abort a slew in progress."""
        return await self._request("GET", "equipment/mount/slew/stop")

    async def mount_set_park_position(self) -> Any:
        """Store the mount's current position as its park position."""
        return await self._request("GET", "equipment/mount/set-park-position")

    async def mount_sync(self, ra: float, dec: float) -> Any:
        """Tell the mount it is currently pointing at RA/Dec (degrees)."""
        return await self._request(
            "GET", "equipment/mount/sync", params={"ra": ra, "dec": dec}
        )

    # -- Camera --------------------------------------------------------------

    async def get_camera_info(self) -> Any:
        return await self._request("GET", "equipment/camera/info")

    async def camera_connect(self) -> Any:
        return await self._request("GET", "equipment/camera/connect")

    async def camera_disconnect(self) -> Any:
        return await self._request("GET", "equipment/camera/disconnect")

    async def camera_cool(self, temperature: float, minutes: float = 0) -> Any:
        """Cool down to `temperature` over `minutes` (0 = as fast as possible)."""
        return await self._request(
            "GET",
            "equipment/camera/cool",
            params={"temperature": temperature, "minutes": minutes, "cancel": "false"},
        )

    async def camera_warm(self, minutes: float = 0) -> Any:
        """Warm the sensor back up over `minutes`."""
        return await self._request(
            "GET",
            "equipment/camera/warm",
            params={"minutes": minutes, "cancel": "false"},
        )

    async def camera_cancel_cooling(self) -> Any:
        """Abort a running cool/warm cycle."""
        return await self._request(
            "GET", "equipment/camera/warm", params={"cancel": _bool(True), "minutes": 0}
        )

    async def camera_set_dew_heater(self, on: bool) -> Any:
        return await self._request(
            "GET", "equipment/camera/dew-heater", params={"power": _bool(on)}
        )

    async def camera_set_binning(self, binning: str) -> Any:
        """binning: NINA's string form, e.g. '1x1', '2x2'."""
        return await self._request(
            "GET", "equipment/camera/set-binning", params={"binning": binning}
        )

    async def camera_set_usb_limit(self, limit: int) -> Any:
        return await self._request(
            "GET", "equipment/camera/usb-limit", params={"limit": limit}
        )

    async def camera_set_readout_mode(self, mode: int) -> Any:
        return await self._request(
            "GET", "equipment/camera/set-readout", params={"mode": mode}
        )

    async def camera_abort_exposure(self) -> Any:
        return await self._request("GET", "equipment/camera/abort-exposure")

    async def camera_capture(
        self,
        duration: float | None = None,
        gain: int | None = None,
        solve: bool = False,
        save: bool = False,
        wait_for_result: bool = False,
    ) -> Any:
        """Take a single exposure.

        `omitImage` is always set: Home Assistant has no use for the base64
        payload here and it would bloat every response.
        """
        params: dict[str, Any] = {
            "solve": _bool(solve),
            "save": _bool(save),
            "waitForResult": _bool(wait_for_result),
            "omitImage": _bool(True),
        }
        if duration is not None:
            params["duration"] = duration
        if gain is not None:
            params["gain"] = gain
        return await self._request("GET", "equipment/camera/capture", params=params)

    async def get_camera_capture_statistics(self) -> Any:
        return await self._request("GET", "equipment/camera/capture/statistics")

    # -- Sequence ------------------------------------------------------------

    async def get_sequence_state(self) -> Any:
        """Return the running sequence as a nested list with per-item status.

        Shape: [{"GlobalTriggers": [...]}, {"Name", "Status", "Items"?, ...}]
        Raises NinaApiResponseError with StatusCode 409 when no sequence is
        loaded, which callers are expected to treat as "idle", not failure.
        """
        return await self._request("GET", "sequence/state")

    async def get_sequence_json(self) -> Any:
        """Return the full sequence definition (heavier than the state call)."""
        return await self._request("GET", "sequence/json")

    async def sequence_start(self, skip_validation: bool = False) -> Any:
        return await self._request(
            "GET", "sequence/start", params={"skipValidation": _bool(skip_validation)}
        )

    async def sequence_stop(self) -> Any:
        return await self._request("GET", "sequence/stop")

    async def sequence_reset(self) -> Any:
        """Reset every item's progress back to CREATED."""
        return await self._request("GET", "sequence/reset")

    async def sequence_skip(self, skip_type: str) -> Any:
        """skip_type: 'CurrentItems', 'ToEnd' or 'ToImaging'."""
        return await self._request(
            "GET", "sequence/skip", params={"type": skip_type}
        )

    async def sequence_list_available(self) -> Any:
        """Return the sequence names available in the configured folder."""
        return await self._request("GET", "sequence/list-available")

    async def sequence_load(self, sequence_name: str) -> Any:
        """Load one of the sequences returned by `sequence_list_available`."""
        return await self._request(
            "GET", "sequence/load", params={"sequenceName": sequence_name}
        )

    async def sequence_set_target(
        self,
        name: str,
        ra: float,
        dec: float,
        rotation: float = 0,
        index: int = 0,
    ) -> Any:
        """Overwrite the target of the target container at `index`."""
        return await self._request(
            "GET",
            "sequence/set-target",
            params={
                "name": name,
                "ra": ra,
                "dec": dec,
                "rotation": rotation,
                "index": index,
            },
        )

    async def sequence_edit(self, path: str, value: str) -> Any:
        """Edit a single sequence property addressed by `path`."""
        return await self._request(
            "GET", "sequence/edit", params={"path": path, "value": value}
        )
