# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] – 2026-09-22

### Added

- **Read-only mode.** A per-entry toggle, offered when adding the integration
  and changeable afterwards under *Configure*, that loads only the reporting
  entities. The `button`, `switch` and `select` platforms are never set up, so
  nothing in Home Assistant can command the rig — not a dashboard, not an
  automation, not Developer tools. Sensors and the event stream are unaffected.
  Turning it on removes the entry's existing control entities from the registry
  instead of leaving them behind as unavailable; turning it off creates them
  again. Defaults to off, so existing entries keep every entity they have.
- **Last frame as its own device.** Thirteen sensors describing the newest
  saved exposure — HFR, star count, filter, exposure time, target, capture
  time, guiding RMS, HFR standard deviation, mean, median, temperature, image
  type and file name. Kept apart from the camera device on purpose: these
  describe one exposure already on disk, not the hardware's current state.
- **The frame itself**, as an `image` entity on that device. Fetched with
  `autoPrepare`, so it is exactly what N.I.N.A. displays rather than a second
  attempt at its stretch and debayering. `image_last_updated` follows the
  capture time rather than the poll interval, so the picture is re-fetched
  when a new frame lands instead of on every update tick. Unavailable until
  the session has saved something.

### Fixed

- The thirteen last-frame sensors have names again. Every one declared a
  translation key and `strings.json` carried them all, but `translations/en.json`
  carried none — and that is the file Home Assistant reads at runtime, so they
  all fell back to the device name and arrived as "Last image 2" through
  "Last image 10".
- The coordinator no longer carries an unresolved stash conflict, which left
  the module with markers in it and unable to import.
- The changelog is valid UTF-8 again; one byte was cp1252 and rendered as a
  replacement character.

## [0.2.1] — 2026-09-20

### Fixed

- Detect running sequences independently of instruction names. Smart Exposure
  reports unnamed internal instructions, which previously appeared inactive.
- Show the parent instruction name for unnamed active steps.
- Recognize running containers between instructions, including empty containers,
  while keeping progress limited to leaf instructions.

The WebSocket improvements below were already present on main and are included
  in this release.


### Added

- **WebSocket push.** A listener holds a connection to `/v2/socket` and
  re-fires every N.I.N.A. event onto the Home Assistant bus as
  `nina_api_event`, carrying the event name in `type` and any extra payload in
  `data`. This exposes things polling cannot see at all — `SEQUENCE-STARTING`,
  `SEQUENCE-FINISHED`, `IMAGE-SAVE`, `AUTOFOCUS-FINISHED`, `MOUNT-BEFORE-FLIP`,
  `SAFETY-CHANGED`, `ERROR-AF` and the rest. Event names are not hardcoded, so
  events added by future plugin versions (or by Target Scheduler) are forwarded
  as well.
- Each event also triggers an immediate, debounced state refresh, so entities
  no longer wait up to a full poll interval after something happens.

### Changed

- `iot_class` back to `local_push` now that the websocket exists.
- The listener reconnects on its own with a capped exponential backoff and
  never blocks setup: with N.I.N.A. closed the integration simply stays on its
  poll interval, and the first failure is logged once rather than every retry.

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
