# pyVCI Tool Register

Every tool in `pyVCI.extension`. Check here before starting a new one — if
something close already exists, extend it instead of duplicating.

pyVCI is a separate pyRevit extension from pyNBT, built for distributing
tools to the whole VCI team (not just NBT's own personal tab). Same build
conventions as pyNBT — see `rules/01-structure.md`.

## pyVCI.tab

### Update.panel

| Tool | Folder | Status | Purpose |
|---|---|---|---|
| Update | `Update.pushbutton` | active (v1.0.0, scaffolded 2026-11-20 — not yet pushed to GitHub, needs device-side GitHub setup + first live Revit test) | Pull the latest pyVCI tools from the shared GitHub repo and reload pyRevit automatically. Checks the latest published **Release** (not the latest `main` commit), asks Yes/No before downloading, then mirror-syncs (adds/updates/removes) the whole extension folder, protecting `.git` from deletion. |
