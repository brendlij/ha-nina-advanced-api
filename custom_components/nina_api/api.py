"""Thin async client for the N.I.N.A. Advanced API.

This module has no Home Assistant imports so it can be unit tested in
isolation and reused outside of HA if needed.

API reference: https://bump.sh/christian-photo/doc/advanced-api/
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE_PATH, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class NinaApiError(Exception):
    """Raised for any transport-level or unexpected-shape error."""


class NinaApiConnectionError(NinaApiError):
    """Raised when the NINA instance cannot be reached."""


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
        return f"ws://{self._host}:{self._port}/{API_BASE_PATH}/socket"

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Perform a request and unwrap NINA's standard envelope."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            async with self._session.request(
                method,
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            ) as resp:
                # NINA returns 200 even for some application errors, but
                # be defensive about transport-level HTTP errors too.
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except aiohttp.ClientConnectionError as err:
            raise NinaApiConnectionError(
                f"Cannot connect to NINA at {self._host}:{self._port}"
            ) from err
        except TimeoutError as err:
            raise NinaApiConnectionError(
                f"Timeout connecting to NINA at {self._host}:{self._port}"
            ) from err
        except aiohttp.ClientResponseError as err:
            raise NinaApiError(f"HTTP error from NINA: {err.status}") from err
        except (ValueError, aiohttp.ContentTypeError) as err:
            raise NinaApiError("Invalid JSON response from NINA") from err

        if not isinstance(data, dict):
            raise NinaApiError(f"Unexpected response shape from NINA: {data!r}")

        if data.get("Success") is False:
            raise NinaApiResponseError(
                data.get("Error") or "Unknown NINA API error",
                status_code=data.get("StatusCode"),
            )

        return data.get("Response")

    # -- Application / connection status ---------------------------------

    async def get_application_info(self) -> Any:
        """Basic reachability + version check.

        Used both by config_flow validation and the coordinator.
        """
        return await self._request("GET", "application/info")

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
        """tracking_mode: NINA TrackingMode enum (0=Sidereal, 5=Stop, ...)."""
        return await self._request(
            "GET", "equipment/mount/tracking", params={"mode": tracking_mode}
        )

    # -- Camera --------------------------------------------------------------

    async def get_camera_info(self) -> Any:
        return await self._request("GET", "equipment/camera/info")

    async def camera_connect(self) -> Any:
        return await self._request("GET", "equipment/camera/connect")

    async def camera_disconnect(self) -> Any:
        return await self._request("GET", "equipment/camera/disconnect")

    async def camera_set_cooler(self, on: bool) -> Any:
        return await self._request(
            "GET", "equipment/camera/cool", params={"power": "on" if on else "off"}
        )
