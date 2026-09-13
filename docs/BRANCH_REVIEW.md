# Existing branches and leftover “fixes”

Reviewed against `origin/main` (commit `b06d3bb`) and the current local `main` (7 commits behind; the only file difference is `manifest.json` funding/JSON). No branches were merged as part of this review.

## Timeline on `origin/main`

| When | What |
| --- | --- |
| 2025-06 / 2025-07 | Integration written and released as 5.6.0 |
| 2025-07-07 | Cursor branch `cursor/fix-three-bugs-in-the-codebase-eb78` opened |
| 2025-07-07 | Merged as PR #1 |
| 2025-07-07 | Immediately reverted as PR #2 (`revert-1-cursor/fix-three-bugs-in-the-codebase-eb78`) |
| after revert | `manifest.json` updated on main: `funding` block removed, JSON becomes valid |
| 2025-07-25 | Draft PR #3 / branch `cursor/review-esp-home-device-configuration-7a0c` (ESPHome LilyGo config) |
| 2025-10 → 2026-02 | Four Snyk bot branches / PRs #5–#8 pinning transitive Python deps in `requirements.txt` |

Current `origin/main` is the original 5.6.0 code plus the post-revert manifest cleanup. The Cursor “three bugs” edits are **not** in main.

## `cursor/fix-three-bugs-in-the-codebase-eb78` (PR #1, reverted)

Commits: `62e14e0` (code), `5526ab2` (changelog 5.7.0), `86f86c2` (version `5.7.0-beta` + missing JSON comma).

The attached `bug_analysis_report.md` claimed three bugs. Verdict from reading the pre-fix code:

### 1. Device-tracker closure — claimed high severity

Original code:

```python
@callback
def _state_change_handler(event, sn=serial_number):
    ...
```

Default-argument binding (`sn=serial_number`) **already captures the current loop value**. The factory-function rewrite is equivalent, not a functional fix. Harmless if re-applied; not a reason to merge that branch.

### 2. Temperature parsing — claimed medium

The branch treated additional hex patterns as invalid, including `"0000"`, and dropped values outside −50…600 °C.

`"0000"` decodes to `0.0 °C` with the existing formula. Treating it as “disconnected” would hide a real reading. `"ffff"` already produces an absurd temperature; a range clamp could be useful, but not as packaged here.

**Do not restore this change as-is.**

### 3. Config-flow “input validation” — claimed security

Regex email checks, length limits, and `.strip().lower()` on the email. Otto Wilde auth is the real validator. Lowercasing the email can break accounts if the API is case-sensitive. This is not a security boundary for a local HA form that already POSTs to Otto Wilde.

**Do not restore this change.**

### What that branch got right

`86f86c2` added the missing comma after `loggers` in `manifest.json`. That was a real packaging bug. `origin/main` later avoided the comma problem by deleting `funding` instead. If funding is restored, the comma is required.

## `revert-1-cursor/fix-three-bugs-in-the-codebase-eb78` (PR #2)

Restored 5.6.0 behaviour. Given (2) and (3) above, reverting was the correct call. The real OptionsFlow / HA 2025.12 break was not in that branch and is still present.

## `cursor/review-esp-home-device-configuration-7a0c` (draft PR #3)

Adds two copies of an ESPHome YAML for a LilyGo T5 e-paper display. It does not touch the G32 integration. Treat as a misplaced Cursor agent run. Do not merge into this repo.

## Snyk branches (PRs #5, #6, #7, #8)

| Branch | Pins in `requirements.txt` |
| --- | --- |
| `snyk-fix-0269ecd43b199280eda30d02922c4bb7` | `idna>=3.7` |
| `snyk-fix-c97a2fc8f32578e3b9841ad99849836b` | `urllib3>=2.6.0` |
| `snyk-fix-b975d5f9a767990f080eb3378394ba91` | `aiohttp>=3.13.3`, `urllib3>=2.6.3` |
| `snyk-fix-72d6a539d91477da834bfbafeca8cb70` | `cryptography>=46.0.5`, `idna>=3.7` |

Home Assistant loads this component via `manifest.json` `requirements` (currently `[]`) and uses HA Core’s own `aiohttp` / `idna` / `cryptography`. Pinning those in a root `requirements.txt` does not change what runs inside HA and can fight Core’s dependency set.

**Do not merge these as a “security fix” for the integration.** Close or ignore unless this repo grows a standalone non-HA client.

## Open GitHub issues that match the code

| Issue | Match |
| --- | --- |
| [#10](https://github.com/zaubii/owg-g32-ha-integration/issues/10) Options flow crash on HA ≥ 2025.12 | Exact match: `OttoWildeG32OptionsFlowHandler.__init__` assigns `self.config_entry`. |
| [#4](https://github.com/zaubii/owg-g32-ha-integration/issues/4) TCP attempts, no connection, “no log messages” | Compatible with several code paths (90s first-packet timeout, missing `popKey`, tracker disabling the switch, log level). Not diagnosed from code alone. |

## Salvage list (if we pick anything up later)

| Take | From | Use |
| --- | --- | --- |
| Valid `manifest.json` | origin/main and/or `86f86c2` | Keep JSON valid; optionally restore `funding` **with** a comma |
| OptionsFlow without setting `config_entry` | not in any branch; described in issue #10 | P0 fix, new work |
| Factory callback | Cursor branch | optional style only |
| Temp range clamp | Cursor branch | maybe later, never treat `0000` as invalid |
| Snyk pins | Snyk branches | no |
| ESPHome YAML | PR #3 | no (wrong project) |
