# CLAUDE.md

Tabletop Simulator (TTS) modding. Created 2026-10-14 by gathering work that was scattered across the
home folder, two E: drive folders and a cloud session's git branch. First (and so far only) mod:
`mods/legendary-marvel/`, a Legendary: Marvel universal table with an in-game menu, scenario browser,
turn flow, trackers and a card reference.

## Where things live

| Thing | Location | In git |
|---|---|---|
| Pipeline scripts (build save, Lua generators, catalog, icons, reference) | `mods/legendary-marvel/scripts/` | yes |
| Hand-corrected data, catalog, scenarios, specs | `mods/legendary-marvel/data/` | yes |
| One-step install package | `mods/legendary-marvel/dist/` | yes |
| Oct 13 discovery work: matching, rescue, OCR, audits, their logs and final CSVs | `mods/legendary-marvel/research/` | yes |
| Card text exports (BGG wiki, "Complete Card Text") | `mods/legendary-marvel/source-text/` | yes |
| **Card art, 7.5G** | `E:\Legendary_TTS_Assets\img\` | no |
| **Generated saves** (12.8MB JSON each) | `E:\Legendary_TTS_Assets\*.json` | no, rebuild with `scripts/build_save.py` |
| **Raw working area, 15G** (`orig\`, `new\`, thumbs, caches, OCR text) | `E:\Media\Board Games\TTS_work\` | no |
| Source scans | `E:\Media\Board Games\Marvel Legendary Cards\` | no |
| TTS's own Saves and Workshop mods | `E:\Documents\My Games\Tabletop Simulator\` | no |

## Important: scripts still hardcode paths

The scripts read and write absolute `E:\Media\Board Games\TTS_work\...` and `E:\Legendary_TTS_Assets`
paths (and used to run from `C:\Users\steph`). Copies in `data/` are for versioning; the scripts
themselves still read the `TTS_work` copies. Edit one place only: if you change a file in `data/`,
copy it to `TTS_work` too (or fix the scripts to use one root; see Open items).

## Provenance

- Source of truth at gather time: branch `claude/adoring-hopper-02yzx7` of `shibpshman/private`
  (top 48 commits, Oct 14 06:54-12:52, files under `deliver/`). The home-root copies were
  identical to it apart from line endings, except `install.py`, where the branch is newer.
- Files not on the branch (the Oct 13 research scripts, `expansion_names.json`, `reference_data.json`,
  `titles.json`, `manifest.json`, logs, CSVs) came from the home folder and `TTS_work`.
- Superseded versions stay on E: only (`matches_v1..v3`, `*_1829020636`, `cache_backup\`).

## Open items

- Replace hardcoded paths with a single `paths.py` / config root so scripts run from the repo.
- `E:\Legendary_TTS_Assets\scripts\` is an older copy of four scripts; retire it once confirmed.
- Decide whether the cloud session transcript should be exported for decision history.
- Large generated saves are not versioned; consider tracking only the release save.
