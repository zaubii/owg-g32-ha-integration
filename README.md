# Otto Wilde G32 Grill Integration for Home Assistant

Monitor your Otto Wilde G32 smart grill in Home Assistant: zone and probe temperatures, gas level, firebox and light status, and connection health.

This is a **cloud** integration (`cloud_push`). Home Assistant talks to Otto Wilde’s servers — there is **no direct local/LAN** link to the grill.

**Current version:** 5.7.0 · **Requires Home Assistant:** 2024.11.0 or newer

### What’s new in 5.7.0

* **Configure works on Home Assistant 2025.12+** (Options flow fix).
* Invalid credentials start a **reauthentication** flow; temporary cloud outages are retried automatically.
* If the live data stream goes silent for about **90 seconds**, the integration reconnects instead of freezing sensors.
* Packaging correctly reports **Cloud Push** (not local push).

## Features

* **Live sensors** from the Otto Wilde cloud data stream (zones, probes, gas, lid, light).
* **Optional Smart Connection Control** via a `device_tracker` (see below).
* **Connection Enabled** switch per grill, with rapid retry then backoff, and auto-disable after long outages.
* **Multi-grill** support for one Otto Wilde account.
* **Diagnostic counters** that survive Home Assistant restarts.
* **Last Data Received** timestamp for connection-health automations.

## Important prerequisites (Otto Wilde app)

Do these in the official app **before** setting up the integration:

1. Connect the G32 to Wi‑Fi.
2. Link the grill to your Otto Wilde account.
3. Set a clear **nickname** (used for Home Assistant entity IDs). Changing it later can change entity IDs.
4. Enable **Show in Dashboard**.
5. Set preferred connection to **Wi‑Fi** or **Wi‑Fi and Bluetooth** (Bluetooth-only will not send cloud data).

## How it works

1. The grill pushes status packets to Otto Wilde over the internet.
2. On setup (and when needed), this integration logs into the Otto Wilde API with your email and password, loads your grill list, and gets a subscribe key per grill.
3. It opens a persistent connection to Otto Wilde’s realtime server and listens for your grill’s packets.

Your Otto Wilde password is stored in the Home Assistant config entry (same pattern as many cloud integrations). If the password changes, Home Assistant will prompt you to reauthenticate.

### Connection Enabled switch

Each grill has a **Connection Enabled** switch:

* On = the integration tries to keep the cloud data stream connected.
* Off = no reconnect attempts for that grill.
* Turns **off automatically** after about **30 minutes** in long-term backoff if the grill stays unreachable.
* If you linked a **device_tracker** and it is **not** `home`, the switch is also turned **off**. Turn it back on (or wait until the tracker is `home` and enable it again) when you want data.

### Smart Connection Control (optional)

If a router or other integration exposes a `device_tracker` for the grill’s Wi‑Fi client:

1. **Settings → Devices & Services → Otto Wilde G32 Grill → Configure**
2. Pick a tracker per grill (or leave blank).
3. When the tracker becomes `home`, the integration tries to connect if the connection is currently disabled.

## Installation (HACS)

1. HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/zaubii/owg-g32-ha-integration` as category **Integration**.
3. Install **Otto Wilde G32 Grill**, restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → Otto Wilde G32 Grill**.
5. Sign in with your Otto Wilde email and password.

## Entities

See **[docs/ENTITIES.md](docs/ENTITIES.md)** for the full list.

Summary per grill: Zone 1–4, Probe 1–4, Gas Weight, Gas Level, Last Data Received, Firebox, Light, Gas Low, Connection Enabled, optional GasBuddy sensors, and diagnostic counters. **Raw Hex Dump** is disabled by default.

## Data packet (reference)

Live values come from a 51-byte binary packet. Known layout (0-based bytes):

| Bytes | Field |
| --- | --- |
| 0–1 | Header `a33a` |
| 2–5 | Grill serial (in the stream; not exposed as its own entity) |
| 6–7 … 20–21 | Zone 1–4 and Probe 1–4 temperatures |
| 22–23 | Gas weight (grams) |
| 24 | Lid / firebox (`01` = open) |
| 25 | Light (`01` = on) |
| 26–30 | Unknown |
| 31 | Gas level (%) |
| 32–50 | Unknown |

Temperature encoding: `(first_byte * 10) + (second_byte / 10)`. Hex `9600` means no reading. Gas Low is on when weight &lt; 2200 g.

## Debugging

1. **Settings → Devices & Services → Otto Wilde G32 Grill → ⋮ → Enable debug logging**
2. Check **Settings → System → Logs**

Or in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.otto_wilde_g32: debug
```

Useful checks: **Last Data Received**, **Connection Enabled**, TCP diagnostic counters, and whether a linked device tracker is unexpectedly not `home`.

## Acknowledgements

Community work that helped make this possible:

* [fschwarz86/g32](https://github.com/fschwarz86/g32)
* [ralmoe/g32-docker-client](https://github.com/ralmoe/g32-docker-client)

## Disclaimer

Third-party community integration. Not developed or supported by Otto Wilde GmbH. Use at your own risk.

---

If you find this useful: [buymeacoffee.com/zaubii](https://buymeacoffee.com/zaubii)
