# N.I.N.A. Advanced API — Home Assistant Integration

[![hacs][hacs-badge]][hacs-url]
[![validate][validate-badge]][validate-url]
[![license][license-badge]](LICENSE)

Bring your astrophotography rig into Home Assistant. This integration talks to
[N.I.N.A.][nina] (Nighttime Imaging 'N' Astronomy) through the
[Advanced API plugin][ninaapi] and exposes mount, camera and sequence state as
native entities — with control over tracking, cooling and the running sequence.

<!-- Replace with a real screenshot of your device page. -->

## Quick start

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=brendlij&repository=ha-nina-advanced-api&category=integration)

1. Click the button above to add this repository to HACS, then install it.
   (Or follow the [manual steps](#installation).)
2. Restart Home Assistant.
3. Add the integration:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=nina_api)

4. Enter the IP of the machine running N.I.N.A. and the port from the plugin
   (default `1888`).

## Requirements

- **N.I.N.A.** with the **Advanced API** plugin installed and enabled:
  Options → Plugins → Advanced API → *API Enabled* = ON
- The N.I.N.A. machine reachable from Home Assistant on the local network
- Default port `1888` (no authentication — the plugin does not offer an API key)
- Home Assistant 2024.12 or newer

> [!TIP]
> Verify the API before you start: open `http://<nina-ip>:1888/v2/api/version`
> in a browser. It must return JSON like
> `{"Response":"2.2.15.2","Success":true,...}`.

## Entities

Everything is grouped into four devices under one config entry.

### N.I.N.A.

| Entity | Type | Notes |
| --- | --- | --- |
| Connected | `binary_sensor` | Stays available when N.I.N.A. is closed, so it can report `off` |
| N.I.N.A. version | `sensor` | Diagnostic |
| API version | `sensor` | Diagnostic |

### Mount

| Entity | Type | Notes |
| --- | --- | --- |
| Right ascension, Declination | `sensor` | Formatted strings as shown in N.I.N.A. |
| Altitude, Azimuth | `sensor` | Degrees |
| Sidereal time | `sensor` | |
| Time to meridian flip | `sensor` | Hours |
| Side of pier | `sensor` | `east` / `west` / `unknown` |
| Device | `sensor` | Driver name, diagnostic |
| Connected, Tracking, Parked, At home position, Slewing, Pulse guiding | `binary_sensor` | |
| Tracking | `switch` | Sidereal ↔ stopped |
| Tracking mode | `select` | Sidereal, Lunar, Solar, King, Stopped |
| Park, Unpark, Slew to home, Meridian flip, Stop slew, Set park position | `button` | |

### Camera

| Entity | Type | Notes |
| --- | --- | --- |
| Temperature, Target temperature | `sensor` | °C |
| Cooler power | `sensor` | % |
| State | `sensor` | `idle`, `waiting`, `exposing`, `reading`, `download`, `error` |
| Gain, Offset, Binning | `sensor` | |
| Last download time | `sensor` | Seconds, diagnostic |
| Device | `sensor` | Driver name, diagnostic |
| Connected, Cooling active, At target temperature, Exposing, Dew heater | `binary_sensor` | |
| Cooler | `switch` | Cools to the camera's set point; off warms up |
| Dew heater | `switch` | Only available if the camera supports it |
| Abort exposure, Cancel cooling | `button` | |

### Sequence

| Entity | Type | Notes |
| --- | --- | --- |
| Running, Loaded | `binary_sensor` | |
| Current step | `sensor` | Name of the instruction N.I.N.A. is executing |
| Progress | `sensor` | % of finished instructions, with `items_total` / `items_finished` attributes |
| Start, Stop, Reset | `button` | |
| Skip current step, Skip to imaging, Skip to end | `button` | |

> [!NOTE]
> N.I.N.A. does not have to be running. When it is closed, entities stay in
> place and read as unavailable — they are never removed from the registry.

## Read-only mode

Everything in the tables above is split into two groups: entities that *report*
(`sensor`, `binary_sensor`) and entities that *command* (`button`, `switch`,
`select`). **Read-only mode** loads only the first group.

| Mode | You get | N.I.N.A. can be controlled from HA |
| --- | --- | --- |
| Read / write *(default)* | Everything | Yes |
| Read-only | `sensor`, `binary_sensor` | No |

The control platforms are not set up at all, so nothing can command the rig —
not a dashboard button, not an automation, not Developer tools. The websocket
stays connected: events are read-only too, and keep firing either way.

Pick the mode when you add the integration, or change it later under
Devices & services → N.I.N.A. Advanced API → **Configure**.

> [!WARNING]
> Switching *to* read-only **deletes** this entry's buttons, switches and
> selects from the entity registry — otherwise Home Assistant would keep
> nagging that they are "no longer being provided". Switching back re-creates
> them; they take their old entity IDs again if those are still free, but any
> rename, icon or area you set on them is gone. Sensors are never touched.

## Installation

### HACS (recommended)

Use the [quick start](#quick-start) button, or add it by hand:

1. HACS → Integrations → ⋮ → **Custom repositories**
2. Repository: `https://github.com/brendlij/ha-nina-advanced-api`, category **Integration**
3. Install **N.I.N.A. Advanced API**, then restart Home Assistant
4. Settings → Devices & services → **Add integration** → *N.I.N.A. Advanced API*

### Manual

Copy `custom_components/nina_api` into your Home Assistant `config/custom_components/`
directory and restart.

## Changing settings later

| What | Where |
| --- | --- |
| Host / IP / port | Devices & services → N.I.N.A. Advanced API → ⋮ → **Reconfigure** |
| Polling interval | …same menu → **Configure** (5–3600 s, default 30 s) |
| [Read-only mode](#read-only-mode) | …same menu → **Configure** |

The new address is validated before it is saved, and the entry is updated in
place — entity IDs, history and dashboard cards all survive the change.

## Events

The integration keeps a websocket open to `ws://<host>:<port>/v2/socket` and
re-fires everything N.I.N.A. pushes onto the Home Assistant event bus as
`nina_api_event`. These are *moments*, not states — polling cannot see them.

```yaml
event_type: nina_api_event
event_data:
  type: SEQUENCE-STARTING     # the N.I.N.A. event name
  entry_id: 01JB…             # which N.I.N.A. instance
  data: {}                    # any extra fields the event carried
```

Trigger on one specific event:

```yaml
triggers:
  - trigger: event
    event_type: nina_api_event
    event_data:
      type: SEQUENCE-FINISHED
```

Or catch everything and branch in a template — useful while exploring. Watch
them live in **Developer tools → Events**, listen to `nina_api_event`.

| Group | Events |
| --- | --- |
| Sequence | `SEQUENCE-STARTING`, `SEQUENCE-FINISHED`, `SEQUENCE-ENTITY-FAILED` |
| Imaging | `IMAGE-SAVE`, `API-CAPTURE-FINISHED`, `CAMERA-DOWNLOAD-TIMEOUT` |
| Autofocus | `AUTOFOCUS-STARTING`, `AUTOFOCUS-FINISHED`, `AUTOFOCUS-POINT-ADDED`, `ERROR-AF` |
| Mount | `MOUNT-BEFORE-FLIP`, `MOUNT-AFTER-FLIP`, `MOUNT-HOMED`, `MOUNT-PARKED`, `MOUNT-UNPARKED`, `MOUNT-CENTER` |
| Guider | `GUIDER-START`, `GUIDER-STOP`, `GUIDER-DITHER` |
| Focuser | `FOCUSER-USER-FOCUSED` |
| Filter wheel | `FILTERWHEEL-CHANGED` |
| Dome / roof | `DOME-SHUTTER-OPENED`, `DOME-SHUTTER-CLOSED`, `DOME-SLEWED`, `DOME-SYNCED`, `DOME-HOMED`, `DOME-PARKED`, `DOME-STOPPED` |
| Flat panel | `FLAT-COVER-OPENED`, `FLAT-COVER-CLOSED`, `FLAT-LIGHT-TOGGLED`, `FLAT-BRIGHTNESS-CHANGED` |
| Safety | `SAFETY-CHANGED` |
| Rotator | `ROTATOR-MOVED`, `ROTATOR-MOVED-MECHANICAL`, `ROTATOR-SYNCED` |
| Live stack | `STACK-STATUS`, `STACK-UPDATED` |
| Plate solve | `ERROR-PLATESOLVE` |
| Profile | `PROFILE-ADDED`, `PROFILE-CHANGED`, `PROFILE-REMOVED` |
| Equipment | `<DEVICE>-CONNECTED` / `<DEVICE>-DISCONNECTED` for camera, mount, focuser, filter wheel, rotator, dome, flat, guider, switch, weather, safety |

The list is not hardcoded — any event a future plugin version adds is forwarded
too, and the Target Scheduler plugin publishes its own topics through the same
channel.

Every event also nudges an immediate state refresh, so entities do not wait for
the next poll.

## Automation examples

Cool the camera down as soon as N.I.N.A. comes online:

```yaml
automation:
  - alias: "Cool camera when NINA starts"
    triggers:
      - trigger: state
        entity_id: binary_sensor.n_i_n_a_connected
        to: "on"
    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.camera_cooler
```

Get notified the moment the sequence finishes:

```yaml
automation:
  - alias: "Notify when imaging is done"
    triggers:
      - trigger: event
        event_type: nina_api_event
        event_data:
          type: SEQUENCE-FINISHED
    actions:
      - action: notify.mobile_app
        data:
          message: >-
            Sequence finished — {{ state_attr('sensor.sequence_progress',
            'items_finished') }} steps completed.
```

React to the safety monitor going unsafe — park the mount and stop the run:

```yaml
automation:
  - alias: "Abort on unsafe conditions"
    triggers:
      - trigger: event
        event_type: nina_api_event
        event_data:
          type: SAFETY-CHANGED
    conditions:
      - condition: template
        value_template: "{{ not trigger.event.data.data.IsSafe }}"
    actions:
      - action: button.press
        target:
          entity_id: button.sequence_stop_sequence
      - action: button.press
        target:
          entity_id: button.mount_park
```

> Entity IDs depend on how Home Assistant slugified them at creation. Check
> yours in Developer tools → States.

## Troubleshooting

**"Failed to connect to N.I.N.A."**
Home Assistant cannot reach that host and port at all. Check the IP, the
firewall on the N.I.N.A. machine, and that the plugin's API is switched on.

**"…it is not the N.I.N.A. Advanced API"**
Something answered, but not the API — almost always the wrong port. Confirm
with `http://<nina-ip>:1888/v2/api/version` in a browser.

**Entities show "no longer being provided by the nina_api integration"**
Fixed in v0.2.0. Older versions tore the config entry down whenever N.I.N.A.
was closed. Update, restart, and the entities come back with their original
IDs — do not delete them.

**Anything else** — enable debug logging; every failed request logs its full URL:

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

All endpoint paths, query parameters and response field names in `api.py` are
verified against the plugin's C# source ([`WebService/V2`][routes]) and, where
the DTOs inherit from N.I.N.A. core, against [`TelescopeInfo.cs`][telescopeinfo].

Two things to know before extending it:

- The API serializes **enums as integers** — no `JsonStringEnumConverter` is
  registered. See the lookup maps in `const.py`.
- Boolean query parameters must be lowercase `true`/`false`; Python's `True`
  is not parsed. Use the `_bool()` helper in `api.py`.
- The REST API lives under `/v2/api`, but the websockets are mounted next to
  it at `/v2/socket` — not underneath.

## Credits

- [N.I.N.A.][nina] by Stefan Berg and contributors
- [Advanced API plugin][ninaapi] by Christian Palm

Not affiliated with or endorsed by either project.

## License

[MIT](LICENSE)

[nina]: https://nighttime-imaging.eu/
[ninaapi]: https://github.com/christian-photo/ninaAPI
[routes]: https://github.com/christian-photo/ninaAPI/tree/main/ninaAPI/WebService/V2
[telescopeinfo]: https://github.com/isbeorn/nina/blob/develop/NINA.Equipment/Equipment/MyTelescope/TelescopeInfo.cs
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://github.com/hacs/integration
[validate-badge]: https://github.com/brendlij/ha-nina-advanced-api/actions/workflows/validate.yml/badge.svg
[validate-url]: https://github.com/brendlij/ha-nina-advanced-api/actions/workflows/validate.yml
[license-badge]: https://img.shields.io/github/license/brendlij/ha-nina-advanced-api.svg
