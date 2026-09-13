# Cloud protocol and packet format (from code)

All endpoints and byte offsets below are taken from `const.py` and `api.py`. Nothing here is inferred from the official app beyond what the parser already assumes.

## REST

Base URL: `https://mobile-api.ottowildeapp.com`

| Call | Method | Path | When | Auth |
| --- | --- | --- | --- | --- |
| Login | `POST` | `/login` | Setup, and again if grill fetch gets 401/403 | body `{"email", "password"}` |
| Grill list | `GET` | `/v2/grills` | Once during `async_setup_entry` (plus one retry after re-login) | header `Authorization: {accessToken}` |

Login keeps only `data.accessToken` and `data.user`. Any other token fields in the JSON are discarded.

Grill fetch stores the `data` array on `client.grills`. Fields the rest of the code reads:

| JSON path | Used for |
| --- | --- |
| `serialNumber` | device id, TCP subscribe, entity unique ids |
| `nickname` | device name and hardcoded `entity_id` |
| `popKey` | TCP subscribe payload (`pop`) |
| `firmwareSemanticVersion` | device `sw_version` |
| `gasbuddyInfo.gasCapacity` | static kg sensor + `hw_version` |
| `gasbuddyInfo.tareWeight` | static kg sensor + `hw_version` |
| `gasbuddyInfo.tankInstalledDate` | timestamp sensor “New Gas Installed” |
| `gasbuddyInfo.tsGasConsumed` | timestamp sensor named “Gas Setup Changed” |
| `gasbuddyInfo.tsLastModified` | timestamp sensor named “Gas Consumed” |

The last two name/key pairings are what the code does. The key names and the sensor names do not match, so the mapping is a suspected defect, not a confirmed Otto Wilde semantic.

`async_get_grill_details` retries at most twice. On 401/403 it clears tokens and logs in again. Other HTTP/JSON errors abort the loop and return `False`.

After the initial setup call, this REST surface is never used again for the life of the config entry.

## TCP stream

| Constant | Value |
| --- | --- |
| Host | `socket.ottowildeapp.com` |
| Port | `4502` |
| Transport | `asyncio.open_connection` (no TLS) |

After connect, the client writes one JSON line and flushes:

```json
{"channel":"LISTEN_TO_GRILL","data":{"grillSerialNumber":"<serial>","pop":"<popKey>"}}
```

No further JSON is sent. There is no ping/keepalive in this codebase.

The first read uses `asyncio.wait_for(..., timeout=90)` (`HEARTBEAT_TIMEOUT_SECONDS`). A connection is treated as successful only after that first read returns a non-empty buffer. Later reads also use `asyncio.wait_for(..., timeout=90)` (`PACKET_IDLE_TIMEOUT_SECONDS`). Idle timeout drops the socket and enters the existing rapid/backoff reconnect path.

Incoming bytes are scanned for header `a33a` (`PACKET_HEADER = b'\xa3\x3a'`). When `buffer.find(header)` succeeds and at least 51 bytes remain, one packet is sliced off and parsed. Leftover bytes stay in the buffer. The buffer is not size-capped.

## 51-byte packet

`PACKET_SIZE = 51`. Parsing works on `data.hex()` (102 hex characters). Offsets below are 0-based **bytes**.

| Bytes | Hex chars | Parser key | Decode |
| --- | --- | --- | --- |
| 0–1 | 0–3 | (sync only) | must be `a33a` to enter the parser |
| 2–5 | 4–11 | (not parsed) | present in the stream; not exposed as an entity |
| 6–7 | 12–15 | `zone_1` | temperature |
| 8–9 | 16–19 | `zone_2` | temperature |
| 10–11 | 20–23 | `zone_3` | temperature |
| 12–13 | 24–27 | `zone_4` | temperature |
| 14–15 | 28–31 | `probe_1` | temperature |
| 16–17 | 32–35 | `probe_2` | temperature |
| 18–19 | 36–39 | `probe_3` | temperature |
| 20–21 | 40–43 | `probe_4` | temperature |
| 22–23 | 44–47 | `gas_weight` | `int(hex, 16)` grams |
| 24 | 48–49 | `lid_open` | `True` iff hex `01` |
| 25 | 50–51 | `light_on` | `True` iff hex `01` |
| 26–30 | 52–61 | (not parsed) | skipped |
| 31 | 62–63 | `gas_level` | `int(hex, 16)` percent |
| 32–50 | 64–101 | (not parsed) | skipped |

Derived fields added in the same dict:

- `raw_hex_dump`: full 102-char hex string
- `gas_low`: `gas_weight < 2200`
- `last_data_received`: `datetime.now(timezone.utc)` at dispatch time (not a packet field)

Any `ValueError` / `IndexError` in the parser returns `None` and the packet is dropped.

### Temperature formula

```
if hex == "9600": None
else: (int(hex[0:2], 16) * 10) + (int(hex[2:4], 16) / 10.0)
```

The comparison is case-sensitive (`"9600"` only). `bytes.hex()` produces lowercase, so that sentinel matches. Other sentinels are not handled.

Example: `020a` → `(2 * 10) + (10 / 10) = 21.0`.

## Connection state machine (`_tcp_listener_loop`)

Outer loop runs while `is_grill_enabled(serial)` is true.

Before every connect:

1. If the assigned device tracker is not `home`, call `enable_grill(serial, False)` and `break`.
2. Increment `tcp_connection_attempts[serial]`.
3. `asyncio.open_connection`, send subscribe JSON, wait up to 90s for first bytes.

On a live stream, packets are parsed until the socket closes, an OS/timeout error occurs, the task is cancelled, or the enable flag becomes false.

On failure (no successful first packet, or the live stream drops):

| Stage | Behaviour |
| --- | --- |
| Rapid retry | 5 attempts (`RAPID_RETRY_ATTEMPTS`), 2s apart (`RAPID_RETRY_DELAY_SECONDS`) |
| Backoff | delay `min(300, 30 * 2**attempt)` seconds; `tcp_reconnect_counter` is the attempt index |
| Give up | if backoff has been running longer than 30 minutes (`OVERALL_TIMEOUT_MINUTES`), disable the grill (switch off) |

A successful first packet resets the rapid counter, the backoff counter, and the backoff start timestamp.

`enable_grill(True)` resets backoff state and starts a new listener task if one is not already running. `enable_grill(False)` cancels that task.

## Counters

| Counter | Scope | Incremented when |
| --- | --- | --- |
| `api_login_calls` | account | every `async_login` |
| `api_grills_calls` | account | every grill-list GET attempt (including 401 retries) |
| `tcp_connection_attempts[serial]` | grill | every TCP `open_connection` attempt |
| `tcp_reconnect_counter[serial]` | grill | each backoff sleep; reset on success or on enable |

Diagnostic sensors restore last HA state and add it back into the in-memory counters via `sync_counter`. Global counters (`api_*`) are restored only once per session (`_synced_global_counters`) so multiple grills do not multiply the restored value.
