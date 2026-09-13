# Prioritized todo (bring-up and defect removal)

## Decisions (2026-09-13)

1. **Device tracker not-home:** Keep current behaviour (disable Connection Enabled). Review the reason later — not part of the P0 code change.
2. **GasBuddy / grill REST refresh:** Postponed until we can validate against live `/v2/grills` payloads (and packet captures already under the repo root if needed).
3. **First implementation:** Whole P0 slice (except the tracker-behaviour change in P0.4).

## P0 status

| ID | Item | Status |
| --- | --- | --- |
| P0.1 | Options flow crash (`self.config_entry`) | **Done** in 5.7.0 |
| P0.2 | `ConfigEntryNotReady` / `ConfigEntryAuthFailed` + reauth | **Done** in 5.7.0 |
| P0.3 | `iot_class` → `cloud_push` | **Done** in 5.7.0 |
| P0.4 | Tracker pause vs disable | **Deferred** — keep disable; revisit later |
| P0.5 | Packet idle watchdog | **Done** in 5.7.0 (`PACKET_IDLE_TIMEOUT_SECONDS = 90`) |
| P0.6 | Translations | **Done** in 5.7.0 |

## P1 — correctness (next after discussion / live data)

| ID | Item | Why | Suggested direction | Effort |
| --- | --- | --- | --- | --- |
| P1.1 | Grill list / `popKey` / GasBuddy never refresh | One GET at setup. | **Postponed** pending live API payloads. | M |
| P1.2 | DeviceInfo misuse | `model` is serial; `hw_version` is gas bottle text. | `model="G32"`, `serial_number=...`. | S |
| P1.3 | GasBuddy timestamp names vs JSON keys | Possible swap of `tsGasConsumed` / `tsLastModified`. | Confirm with live payload, then remap. **Postponed** with P1.1. | S |
| P1.4 | Hardcoded `entity_id` from nickname | Fragile sanitization. | Stop setting `entity_id`; `has_entity_name`. | M |
| P1.5 | Unbounded TCP buffer | Header miss grows buffer. | Cap / resync / drop. | S |
| P1.6 | Local tree vs `origin/main` | Manifest was invalid locally. | Addressed in 5.7.0 packaging cleanup. | S |
| P1.7 | Access token only | Combined with P1.1. | Refresh path next to grill refresh. | M |

## P2 — reliability, quality, and HA APIs

| ID | Item | Status / note |
| --- | --- | --- |
| P2.1 | `entry.runtime_data` | Pending |
| P2.2 | Unload options listener | **Done** incidentally in 5.7.0 (`async_on_unload`) |
| P2.3 | `CancelledError` separate path | **Done** incidentally in 5.7.0 TCP loop |
| P2.4 | TCP keepalive | Pending — only if live capture shows need |
| P2.5 | Diagnostics platform | Pending — useful for issue #4 |
| P2.6 | Unit tests | Pending |
| P2.7 | Raise `hacs.json` min HA | **Done** → `2024.11.0` |
| P2.8 | Remove unused `random` import | **Done** in 5.7.0 |
| P2.9 | `gas_level` device class `BATTERY` | Pending |

## P3 — hygiene

| ID | Item | Action |
| --- | --- | --- |
| P3.1 | Cursor “three bugs” branch | Do not re-merge |
| P3.2 | Snyk PRs #5–#8 | Close without merging |
| P3.3 | ESPHome draft PR #3 | Close; wrong repo |
| P3.4 | Quality tooling | Later |
| P3.5 | Issue #4 | After deploy of idle watchdog; gather logs/diagnostics |

## Explicitly out of scope until we agree otherwise

- Writing commands to the grill.
- Local MQTT / ESPHome bridge.
- Decoding unknown packet bytes 26–30 / 32–50 without more captures.
- Re-introducing the reverted 5.7.0-beta Cursor branch.
