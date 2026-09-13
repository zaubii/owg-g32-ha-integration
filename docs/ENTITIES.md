# Entities

One Home Assistant **device** is created for each grill on your Otto Wilde account. Entity IDs are based on the grill **nickname** from the Otto Wilde app (lowercased; spaces and hyphens become underscores). The stable unique ID uses the grill serial number, so renaming in the app can change the suggested entity ID but does not break the device link.

Values update over the Otto Wilde cloud data stream (no polling). GasBuddy fields are read once when the integration loads and do not refresh until you reload the integration.

## Temperatures and gas (live)

| Name | Description |
| --- | --- |
| Zone 1 – Zone 4 | Heating-zone temperatures (°C). Unavailable when the grill reports no reading. |
| Probe 1 – Probe 4 | External meat-probe temperatures (°C). Unavailable when a probe is not connected / not reporting. |
| Gas Weight | Remaining gas weight in grams. |
| Gas Level | Remaining gas as a percentage. |
| Last Data Received | UTC timestamp of the last successfully parsed packet (useful for automations and connection health). |
| Raw Hex Dump | Full packet as hex (diagnostic; disabled by default). |

## Status (live)

| Name | Description |
| --- | --- |
| Firebox | On when the lid / firebox is open. |
| Light | On when the grill light is on. |
| Gas Low | On when gas weight is below 2200 g. |

## GasBuddy (snapshot at setup)

These entities appear only if the Otto Wilde API returns GasBuddy data for the grill.

| Name | Description |
| --- | --- |
| New Gas Installed | Timestamp from GasBuddy for tank install. |
| Gas Setup Changed | Timestamp from GasBuddy (API field as returned at setup). |
| Gas Consumed | Timestamp from GasBuddy (API field as returned at setup). |
| Gas Original Capacity | Configured bottle capacity (kg). |
| Gas Tara Weight | Configured empty bottle weight (kg). |

## Connection and diagnostics

| Name | Description |
| --- | --- |
| Connection Enabled | Master switch for the cloud data stream for this grill. Turn off to stop reconnect attempts. Turns off automatically after ~30 minutes of failed backoff, or when a linked device tracker is not `home`. Turn it back on when the grill is online again. |
| API Login Calls | How many times this account logged into the Otto Wilde API (persists across restarts). |
| API Grills Calls | How many times grill details were fetched from the API (persists across restarts). |
| TCP Connection Attempts | Connection attempts for this grill (persists across restarts). |
| TCP Backoff Counter | Current long-term reconnect attempt count. |
| Next Backoff Attempt | When the next backoff reconnect is scheduled (if backing off). |

For a typical grill with GasBuddy data, expect about **26** entities.
