# Agent instructions — Otto Wilde G32 HA integration

## Read first

1. If `local_dev/docs/HANDOFF.md` exists, **read it before planning or coding**. It is the maintainer handoff (next decisions, PR status, prior choices).
2. User-facing truth: `README.md` and `docs/ENTITIES.md`.
3. Integration code: `custom_components/otto_wilde_g32/`.

## Hard constraints

- **Never commit or push `local_dev/`** — it is gitignored (captures + internal notes).
- Do **not** re-merge the old Cursor “three bugs” branch or Snyk transitive pins in `requirements.txt`.
- This is a **cloud_push** integration (Otto Wilde API + TCP). There is no local grill protocol in-tree.
- Prefer small PRs; confirm breaking entity-ID changes with the user (P1.4).

## Current delivery line

- Active work landed as **5.7.0** on `fix/5.7.0-p0-ha-compatibility` / PR #11 unless merged since.
- Next work is driven by decisions in `local_dev/docs/HANDOFF.md`, not by inventing a new roadmap.
