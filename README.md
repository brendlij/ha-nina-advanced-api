# N.I.N.A. Advanced API – Home Assistant Integration

HACS integration for [N.I.N.A.](https://nighttime-imaging.eu/) via the
[Advanced API plugin](https://github.com/christian-photo/ninaAPI) by Christian Palm.

## Status: v0.1

Covered so far:

- Config flow (host/port, no auth needed — the plugin currently offers no API key)
- **N.I.N.A.**: connection state, N.I.N.A. and API version
- **Mount**: RA/Dec/Alt/Az, sidereal time, time to meridian flip, side of pier,
  tracking/parked/at home/slewing/pulse guiding, tracking mode select,
  park/unpark/home/flip/stop slew/set park position buttons
- **Camera**: temperature, target temperature, cooler power, camera state, gain,
  offset, binning, last download time, connected/cooling/at target temp/exposing/
  dew heater, cooler and dew heater switches, abort exposure and cancel cooling buttons
- **Sequence**: running/loaded, current step, progress in percent,
  start/stop/reset/skip buttons

Planned (v0.2+):

- WebSocket listener for live push instead of pure 30s polling
- Filter wheel, focuser, rotator, dome/roof, guider, safety monitor, flat panel
- Options flow (poll interval)
- Diagnostics export

## Requirements

- N.I.N.A. with the **Advanced API** plugin installed and enabled
  (Options → Plugins → Advanced API → "API Enabled" = ON)
- The machine running N.I.N.A. must be reachable from Home Assistant on the local network
- Default port: `1888`

## Installation (HACS custom repository, until it is in the default store)

1. HACS → Integrations → ⋮ → Custom repositories
2. Add this repository's URL, category "Integration"
3. Install "N.I.N.A. Advanced API", restart Home Assistant
4. Settings → Devices & services → Add integration → "N.I.N.A. Advanced API"
5. Enter host/IP and port (default 1888)

## Troubleshooting

**"Failed to connect to N.I.N.A."** — Home Assistant cannot reach the host and
port at all. Check the IP, the firewall on the N.I.N.A. machine, and that the
plugin's API is switched on.

**"…it is not the N.I.N.A. Advanced API"** — something answered, but not the API.
Almost always the wrong port. Verify by opening
`http://<nina-ip>:1888/v2/api/version` in a browser; it must return JSON.

For anything else, enable debug logging — every failed request logs its full URL:

```yaml
logger:
  logs:
    custom_components.nina_api: debug
```

## Development

```bash
# Symlink into a local HA test instance
ln -s $(pwd)/custom_components/nina_api /path/to/config/custom_components/nina_api
```

All endpoint paths, query parameters and response field names used by
`api.py` were verified against the plugin's C# source
([`ninaAPI/WebService/V2`](https://github.com/christian-photo/ninaAPI/tree/main/ninaAPI/WebService/V2))
and, where the DTOs inherit from N.I.N.A. core, against
[`TelescopeInfo.cs`](https://github.com/isbeorn/nina/blob/develop/NINA.Equipment/Equipment/MyTelescope/TelescopeInfo.cs).

Two things worth knowing when extending it:

- The API serializes enums as **integers**, not strings — no
  `JsonStringEnumConverter` is registered. See the lookup maps in `const.py`.
- Boolean query parameters must be lowercase `true`/`false`; Python's `True`
  would not be parsed. Use the `_bool()` helper in `api.py`.
