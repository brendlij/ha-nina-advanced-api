"""WebSocket listener that forwards N.I.N.A. events onto the HA event bus.

The Advanced API pushes discrete events over ws://<host>:<port>/v2/socket -
sequence start/finish, autofocus results, meridian flips, saved images,
equipment connects. Polling cannot see most of these: they are moments, not
states, and a 30s poll simply misses them.

Every frame is re-fired as a single Home Assistant event type (EVENT_NINA)
carrying the NINA event name, so an automation can trigger on any of them,
including events future plugin versions add.

Frame shape (HttpResponse with Type = "Socket"):
    {"Response": {"Event": "SEQUENCE-STARTING", ...extra...},
     "Error": "", "StatusCode": 200, "Success": true, "Type": "Socket"}
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import NinaApiClient
from .const import (
    DOMAIN,
    EVENT_NINA,
    WS_MESSAGE_TYPE,
    WS_RECONNECT_DELAY,
    WS_RECONNECT_DELAY_MAX,
)
from .coordinator import NinaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class NinaWebsocketListener:
    """Keeps one websocket open to NINA and republishes what it sends."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: NinaApiClient,
        coordinator: NinaDataUpdateCoordinator,
        entry_id: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._hass = hass
        self._client = client
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._session = session
        self._task: asyncio.Task[None] | None = None
        self._connected = False
        # Only the first failure of a run is worth a warning; NINA being
        # closed overnight should not fill the log with the same line.
        self._reported_failure = False

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self, entry: ConfigEntry) -> None:
        """Run the listener as a background task owned by the config entry."""
        self._task = entry.async_create_background_task(
            self._hass, self._run(), name=f"{DOMAIN} websocket"
        )

    async def async_stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self._connected = False

    async def _run(self) -> None:
        """Reconnect forever with a capped exponential backoff."""
        delay = WS_RECONNECT_DELAY
        while True:
            try:
                await self._listen()
                # A clean close means NINA went away; reset the backoff so
                # the next start is picked up promptly.
                delay = WS_RECONNECT_DELAY
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, OSError) as err:
                if not self._reported_failure:
                    _LOGGER.info(
                        "N.I.N.A. websocket unavailable (%s); retrying in the "
                        "background. Polling continues either way", err
                    )
                    self._reported_failure = True
                else:
                    _LOGGER.debug("websocket reconnect failed: %s", err)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error in the NINA websocket listener")
            finally:
                self._connected = False

            await asyncio.sleep(delay)
            delay = min(delay * 2, WS_RECONNECT_DELAY_MAX)

    async def _listen(self) -> None:
        """Hold one connection open until it drops."""
        url = self._client.websocket_url
        _LOGGER.debug("Connecting to NINA websocket at %s", url)

        async with self._session.ws_connect(url, heartbeat=30) as ws:
            self._connected = True
            self._reported_failure = False
            _LOGGER.info("Connected to the N.I.N.A. websocket")
            # State may have moved on while we were disconnected.
            await self._coordinator.async_request_refresh()

            async for msg in ws:
                if msg.type is aiohttp.WSMsgType.TEXT:
                    await self._handle(msg.data)
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break

        _LOGGER.debug("NINA websocket closed")

    async def _handle(self, raw: str) -> None:
        """Turn one frame into a Home Assistant event."""
        try:
            payload = json.loads(raw)
        except ValueError:
            _LOGGER.debug("Ignoring non-JSON websocket frame: %.120s", raw)
            return

        if not isinstance(payload, dict) or payload.get("Type") != WS_MESSAGE_TYPE:
            _LOGGER.debug("Ignoring non-socket frame: %.120s", raw)
            return

        response = payload.get("Response")
        if isinstance(response, dict):
            event = response.get("Event")
            data = {k: v for k, v in response.items() if k != "Event"}
        elif isinstance(response, str):
            # Consumer events are sent as a bare string rather than a table.
            event, data = response, {}
        else:
            _LOGGER.debug("Ignoring frame with no event: %.120s", raw)
            return

        if not event:
            return

        _LOGGER.debug("NINA event %s %s", event, data or "")
        self._hass.bus.async_fire(
            EVENT_NINA,
            {"type": event, "entry_id": self._entry_id, "data": data},
        )

        # Nudge the coordinator so entity state reflects the event without
        # waiting for the next poll. async_request_refresh is debounced, so
        # a burst of events still results in a single fetch.
        await self._coordinator.async_request_refresh()
