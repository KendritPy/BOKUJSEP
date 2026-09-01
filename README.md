# BokuLangToggle

Runtime Japanese/Spanish language-toggle research and PPSSPP plugin for
**Boku no Natsuyasumi Portable** (`UCJS10038`). The intended runtime base is
the GriffithVIII/TraduSquare Spanish v1.0 patched ISO so its horizontal text,
VWF, layout improvements, graphics, and added subtitle support remain intact.

**New agents should start with [docs/HANDOFF.md](docs/HANDOFF.md).** It records
the audited source revisions, current runtime boundary, rejected leads, exact
next experiment, and which facts remain unknown. The static format and public
translation-tool lineage are documented separately in
[docs/boku-dialogue-format.md](docs/boku-dialogue-format.md) and
[docs/spanish-patch-archaeology.md](docs/spanish-patch-archaeology.md).

This repository never modifies an input ISO in place. Generated game data and
copyrighted assets stay under ignored local directories. 

## Current development baseline

- PPSSPP 1.20.4 portable and exact source tag, not a newer `master` snapshot.
- Spanish patch `bokuES-v1.0.xdelta` from the official v1.0 release.
- `snake7594/boku-natsu-portable-kr-patch` v0.1.3 for the current
  CDIMG/dialogue/PIM2 pipeline and fixed-slot evidence.
- `pleonex/Boku-no-Natsuyasumi` at GriffithVIII's public `dae1215...` commit,
  which includes the non-default Yarhl/PO rewrite, extended table, and second
  font sheet.
- `xan1242/PSPModBase` plus its bundled Windows PSPSDK for PRX builds.

## One-time local setup

Place a legally obtained clean Japanese ISO at `input/jp/Boku_JP.iso`, then run:

```powershell
./scripts/setup.ps1
./scripts/pipeline.ps1
./scripts/build.ps1
./scripts/deploy.ps1
```

The setup script hashes the clean ISO, validates it against the known retail
MD5 when possible, and creates `input/es/Boku_ES.iso` with the official xdelta
patch. The pipeline extracts both filesystems and CDIMG archives, emits file
diffs and structured dialogue, and builds the first structural bilingual map.

`tools/ppsspp_debug.py` talks to the exact PPSSPP 1.20.4 debugger protocol. Its
`hotkey` command turns one host F7 press into the otherwise-unused PSP Note
button; the PRX edge-detects that guest button and toggles exactly once. F7 is
not part of PPSSPP's default PSP or emulator hotkey map (unlike F12, which opens
the debugger). F5 and F6 are also available as explicit helper alternatives.

The current PRX is the safe milestone-zero loader/input build. Dialogue hooks
remain deliberately disabled until the user's exact Spanish EBOOT signature
and runtime text path have been measured.

For development, `launch-dev.bat` deploys the current PRX, starts the project
PPSSPP build with the Spanish ISO, waits for its debugger service, and starts
the F7 bridge automatically. `build.bat` and `install.bat` avoid local
PowerShell execution-policy issues.
