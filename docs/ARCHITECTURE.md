# Architecture (from code)

This document describes what the repository actually implements. It is derived from the Python modules under `custom_components/otto_wilde_g32/` and the packaging files. User-facing README claims that are not present in code are omitted.

## What this integration is

A Home Assistant custom component (`domain`: `otto_wilde_g32`) that:

1. Logs into the Otto Wilde cloud REST API with the account email and password from the config entry.
2. Fetches the list of grills for that account.
3. Opens one persistent TCP connection per grill to a cloud socket and listens for 51-byte binary status packets.
4. Exposes temperatures, gas readings, lid/light flags, diagnostic counters, and a connection on/off switch as HA entities.

There is no local grill discovery, no LAN protocol, and no command path back to the grill. The component is read-only.

## Repository layout

```
custom_components/otto_wilde_g32/
  __init__.py       Config-entry setup, device registry, device-tracker options
  api.py            REST login, grill fetch, TCP listener, packet parser, retry state
  config_flow.py    UI setup (email/password) and options flow (device_tracker per grill)
  const.py          Domain, platforms, URLs, TCP host/port, retry constants
  sensor.py         TCP sensors, GasBuddy static sensors, liveness, diagnostics
  binary_sensor.py  Firebox, light, gas-low
  switch.py         Connection Enabled
  manifest.json     HACS/HA integration metadata
hacs.json           HACS catalog metadata
requirements.txt    Contains only `homeassistant` (not used by HA to install this component)
```

There are `strings.json` / `translations/en.json` for config and options flows. There is no `diagnostics.py`, no tests, no services, and no CI config.

## Runtime object graph

One config entry represents one Otto Wilde **account**, not one grill.

```
HomeAssistant
  hass.data["otto_wilde_g32"][entry_id] = OttoWildeG32ApiClient
      .grills[]                  REST payload, one dict per grill
      ._tokens["access_token"]   from POST /login
      ._tcp_connections[serial]  {"task": asyncio.Task}
      ._enabled_grills[serial]   bool, default True
      ._device_trackers[serial]  optional entity_id
      ._update_callbacks         TCP packet -> sensors / binary sensors / liveness
      ._state_update_callbacks   enable/disable -> Connection Enabled switch
      ._diagnostics_callbacks    counters -> diagnostic sensors
      ._counters                 api_login_calls, api_grills_calls,
                                 tcp_connection_attempts[serial],
                                 tcp_reconnect_counter[serial]
```

Platforms (`sensor`, `binary_sensor`, `switch`) are forwarded from `async_setup_entry`. Each entity registers a callback on the shared client and does not poll.

## Setup sequence (`__init__.py`)

`async_setup_entry`:

1. Build `OttoWildeG32ApiClient(email, password, aiohttp session, hass)`.
2. Store it on `hass.data[DOMAIN][entry.entry_id]`.
3. Call `async_get_grill_details()`. `AuthenticationError` → `ConfigEntryAuthFailed` (reauth). `CannotConnectError` → `ConfigEntryNotReady` (retry).
4. For each grill, create a device-registry entry keyed by `(DOMAIN, serialNumber)`.
5. Call `async_update_options` once (bind device trackers from `entry.options`).
6. Register `async_update_options` as an options update listener (unloaded via `async_on_unload`).
7. Forward platform setups.
8. Start TCP listeners for every grill whose `_enabled_grills` flag is true (all of them, on first setup).
9. Register a one-shot `EVENT_HOMEASSISTANT_STOP` handler that stops listeners.

`async_unload_entry` stops listeners, unloads platforms, and pops the client from `hass.data`.

## Device registry fields (as written)

For each grill:

| DeviceInfo field | Source in code |
| --- | --- |
| `identifiers` | `(otto_wilde_g32, serialNumber)` |
| `name` | `nickname`, else `"G32 {serial[:6]}"` |
| `model` | the serial number (not a model name) |
| `manufacturer` | `"Otto Wilde"` |
| `sw_version` | `firmwareSemanticVersion` |
| `hw_version` | `"Capacity: {gasCapacity}kg, Tare: {tareWeight}kg"` from `gasbuddyInfo` |

`serial_number=` is not set. Gas bottle metadata is stored in `hw_version`.

## Options: device tracker binding

Options keys are `device_tracker_{serialNumber}` -> a `device_tracker` entity id.

`async_update_options` unsubscribes previous state listeners, then for each grill:

- Stores the entity id on the client (`register_device_tracker`).
- If an entity is selected, listens for state changes. On `home`, it calls `connect_if_needed(serial)`.
- If the current state is already `home`, it also calls `connect_if_needed`.

If no tracker is assigned, `_is_device_tracker_home` returns `True` (connection attempts are allowed).

If a tracker **is** assigned and its state is anything other than `"home"` (including `not_home`, `unknown`, `unavailable`), the TCP loop treats that as “not home”, calls `enable_grill(serial, False)`, and exits. That turns the Connection Enabled switch off. It does not merely pause retries.

## Config flow

`OttoWildeG32ConfigFlow.VERSION = 1`. Unique id is the email.

`async_step_user` posts login credentials. On success it stores `{email, password, user_info}` in the config entry. There is no reauth step, no password-change path, and no abort-if-already-configured besides unique-id.

`OttoWildeG32OptionsFlowHandler` uses the base-class `self.config_entry` property (no assignment). Reauth is handled by `async_step_reauth` / `async_step_reauth_confirm`.

## Packaging metadata vs code

| File | Claim in file | What the code does |
| --- | --- | --- |
| `manifest.json` `iot_class` | `cloud_push` | Connects to `mobile-api.ottowildeapp.com` and `socket.ottowildeapp.com` |
| `hacs.json` `iot_class` | `Cloud Push` | Same cloud path |
| `hacs.json` `homeassistant` | `2024.11.0` | OptionsFlow uses the base-class `config_entry` property |
| `manifest.json` `version` | `5.7.0` | No other version source of truth |
| `manifest.json` `requirements` | `[]` | Relies on HA’s bundled `aiohttp` |
| `requirements.txt` | `homeassistant` | Unused by HA when loading a custom component |

## What the code does not implement

- Grill control (set temperature, light, ignition, timers).
- Local/Wi-Fi direct connection.
- Token refresh using a refresh token (only `accessToken` is kept).
- Periodic REST refresh of grill list, `popKey`, firmware, or GasBuddy fields.
- A watchdog after the first TCP packet: later `reader.read()` has no timeout.
- Home Assistant diagnostics download (`async_get_config_entry_diagnostics`).
- Translations for config-flow errors (`invalid_auth`, `cannot_connect`, `unknown`, `no_grills_found`).
- Tests.
