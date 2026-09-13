# Entities (from code)

One HA device is created per grill. Entity unique ids are always `{serialNumber}_{suffix}`. Display names are the short suffixes below (`_attr_name`), not “GrillName Zone 1”. `entity_id` is also set explicitly from the Otto Wilde nickname:

```
{nickname.lower().replace(' ', '_').replace('-', '_')}
```

Nickname characters other than space and hyphen are not stripped. Changing the nickname in the Otto Wilde account therefore changes the intended `entity_id` on the next setup; `unique_id` stays on the serial.

None of the entities poll (`_attr_should_poll = False`).

## TCP sensors (`sensor.py` / `G32TcpSensor`)

Source: parsed packet dict.

| Unique-id suffix | Name | Device class | Unit | Notes |
| --- | --- | --- | --- | --- |
| `zone_1` … `zone_4` | Zone 1–4 | temperature | °C | `None` when hex is `9600` |
| `probe_1` … `probe_4` | Probe 1–4 | temperature | °C | same |
| `gas_weight` | Gas Weight | weight | g | unsigned 16-bit from bytes 22–23 |
| `gas_level` | Gas Level | **battery** | % | byte 31; battery class is what the code sets |
| `raw_hex_dump` | Raw Hex Dump | — | — | diagnostic, disabled by default |

Temperature / weight / battery sensors use `state_class = measurement`.

## GasBuddy static sensors (`G32StaticSensor`)

Created only if the corresponding `gasbuddyInfo` key is present (timestamps) or not `None` (weights). Values are captured once at platform setup from the REST snapshot. They never receive TCP or later REST updates.

| Unique-id suffix | Name | REST key | Device class | Unit |
| --- | --- | --- | --- | --- |
| `gas_installed` | New Gas Installed | `tankInstalledDate` | timestamp | — |
| `gas_changed` | Gas Setup Changed | `tsGasConsumed` | timestamp | — |
| `gas_consumed` | Gas Consumed | `tsLastModified` | timestamp | — |
| `gas_original_capacity` | Gas Original Capacity | `gasCapacity` | weight | kg |
| `gas_tara_weight` | Gas Tara Weight | `tareWeight` | weight | kg |

ISO timestamps with a trailing `Z` are converted via `value.replace("Z", "+00:00")` then `datetime.fromisoformat`.

## Liveness (`G32LivenessSensor`, RestoreEntity)

| Unique-id suffix | Name | Device class |
| --- | --- | --- |
| `last_data_received` | Last Data Received | timestamp |

Updated whenever any parsed packet is dispatched. Restores the last HA state on restart. Does not by itself trigger reconnects.

## Diagnostic sensors (`G32DiagnosticSensor`, RestoreEntity)

All `entity_category = diagnostic`.

| Unique-id suffix | Name | State class | Scope |
| --- | --- | --- | --- |
| `api_login_calls` | API Login Calls | total_increasing | account (same value on every grill device) |
| `api_grills_calls` | API Grills Calls | total_increasing | account |
| `tcp_connection_attempts` | TCP Connection Attempts | total_increasing | per grill |
| `tcp_reconnect_counter` | TCP Backoff Counter | total_increasing | per grill |
| `next_connection_attempt` | Next Backoff Attempt | timestamp | per grill; `None` when not backing off |

Counters restore from last state and call `api_client.sync_counter`. Grill-specific restoration is applied for `tcp_connection_attempts` and `tcp_reconnect_counter` only (`GRILL_SPECIFIC_COUNTERS`).

`next_connection_attempt` naive datetimes are tagged UTC before writing state.

## Binary sensors (`binary_sensor.py`)

| Unique-id suffix | Name | Device class | Packet key | Icon |
| --- | --- | --- | --- | --- |
| `firebox_open` | Firebox | opening | `lid_open` | `mdi:window-opened` / `mdi:window-closed` |
| `light_on` | Light | light | `light_on` | `mdi:wall-sconce-flat` |
| `gas_low` | Gas Low | problem | `gas_low` | default |

Initial `is_on` is `None` until the first packet.

## Switch (`switch.py`)

| Unique-id suffix | Name | Device class |
| --- | --- | --- |
| `connection_enabled` | Connection Enabled | switch |

`is_on` is `api_client.is_grill_enabled(serial)`. Turn on/off calls `enable_grill`. Icon is `mdi:lan-connect` or `mdi:lan-disconnect`.

The switch is also written by the TCP loop: 30-minute backoff timeout and “tracker not home” both call `enable_grill(..., False)`.

## Entity count per grill (typical)

If GasBuddy fields are all present: 11 TCP sensors + 5 static + 1 liveness + 5 diagnostic + 3 binary + 1 switch = **26** entities. Missing GasBuddy keys omit those static sensors.
