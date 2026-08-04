# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-08-04

Full sequence, mount and camera coverage, and the integration no longer falls
apart when N.I.N.A. is closed.

### Fixed

- **Setup failed with "Failed to connect" even with a correct IP and a running
  N.I.N.A.** The connection probe called `GET /v2/api/application/info`, which
  does not exist in the Advanced API — N.I.N.A. answered `404`, and the config
  flow reported every error as `cannot_connect`. The probe now uses
  `GET /v2/api/version`.
- **All entities vanished with "no longer being provided by the nina_api
  integration" whenever N.I.N.A. was closed.** A closed N.I.N.A. was raised as
  an update failure, so the config entry never loaded and Home Assistant
  dropped the entities. It is now a normal state: the refresh succeeds with the
  connection flag off, entities stay registered and read as unavailable, and
  the connectivity sensor stays readable so it can report `off`. Entities
  return with their original IDs — history and dashboards are preserved.
- Camera cooling called `equipment/camera/cool?power=on`, which is not the real
  signature. It now uses `cool?temperature=&minutes=&cancel=` and the separate
  `warm` route.
- The websocket URL pointed at `/v2/api/socket`; the socket modules are mounted
  at `/v2/socket`, next to the REST API rather than underneath it.
- Boolean query parameters were serialized as Python's `True`/`False`, which
  the API's query parser does not accept. They are now lowercase.
- Enum fields (tracking mode, camera state, side of pier) were read as strings.
  The API serializes enums as integers; they are mapped back to readable states.

### Added

- **Sequence support**: running/loaded state, the name of the currently
  executing instruction, progress in percent with `items_total` and
  `items_finished` attributes, plus start, stop, reset and three skip buttons.
- **Reconfigure flow** — change host and port after setup. The new address is
  validated before being saved and the entry is updated in place, so entity
  IDs, history and dashboard cards survive the move.
- **Options flow** — configurable polling interval (5–3600 s, default 30 s).
- **New platforms**: `switch` (camera cooler, dew heater, mount tracking) and
  `select` (mount tracking mode). Switches that depend on hardware capabilities
  report unavailable when the device does not support them.
- Mount: sidereal time, time to meridian flip, side of pier, at-home and
  pulse-guiding state, driver name, and meridian flip / stop slew / set park
  position buttons.
- Camera: target temperature, camera state, gain, offset, binning, last
  download time, driver name, at-target-temperature and exposing state, and
  abort exposure / cancel cooling buttons.
- N.I.N.A. and API version sensors.
- API client coverage grew from 9 to 44 endpoints, including the full sequence
  surface, mount slew/flip/sync and camera capture.
- Distinct error messages in the config flow: unreachable host, wrong service
  on the port, and an application-level error are no longer all reported as
  "cannot connect". Every failed request logs its full URL at debug level.

### Changed

- The UI is English everywhere; the German translation was removed.
- `iot_class` corrected from `local_push` to `local_polling` — the websocket
  listener does not exist yet.
- `LICENSE` was an empty file, so the project had no identifiable license. It
  now contains the MIT license.
- `manifest.json` keys sorted as hassfest requires.

## [0.1.0] — 2026-08-04

Initial release.

### Added

- Config flow (host/port, no authentication needed)
- Connection state
- Mount: RA/Dec/Alt/Az, tracking, parked and slewing state, park/unpark/home
  buttons
- Camera: temperature, cooler power, connected and cooling state

[Unreleased]: https://github.com/brendlij/ha-nina-advanced-api/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/brendlij/ha-nina-advanced-api/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/brendlij/ha-nina-advanced-api/releases/tag/v0.1.0
