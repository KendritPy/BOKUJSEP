# BokuLangToggle

BokuLangToggle is an experimental PPSSPP plugin that switches dialogue in
**Boku no Natsuyasumi Portable** (`UCJS10038`) between the original Japanese
and the GriffithVIII/TraduSquare Spanish v1.0 translation while the game is
running.

Press **F7** during a supported dialogue box to toggle languages. Japanese
mode restores the paired original text, Japanese font atlas, and fixed-width
layout; Spanish mode restores the translated text and proportional layout.
If a dialogue record cannot be paired safely, the plugin refuses the switch or
automatically falls back to Spanish.

This repository contains source code and reproducible research tooling only.
It does **not** contain either game ISO, extracted game assets, Sony software,
or the Spanish translation patch.

## What works

- Runtime Japanese/Spanish switching for mapped gameplay dialogue.
- 8,539 structurally paired dialogue records.
- Automatic Spanish fallback for unresolved or page-incompatible records.
- PPSSPP 1.20.4 startup, plugin deployment, debugger configuration, and F7
  bridge through one launcher.
- Savestate recovery when the state was made with the same plugin build.

Menus remain those of the Spanish translation. Cinematics remain Spanish.
Japanese menu restoration was tested and rejected because menu resources share
font/layout state with the dialogue renderer and produced unsafe mixed states.

## Requirements

- Windows 10 or 11
- Git and PowerShell 5.1 or newer
- Python 3.10 or newer
- A legally obtained clean Japanese `UCJS10038` ISO
- Internet access for the one-time dependency bootstrap

The audited emulator target is **PPSSPP 1.20.4 x64**. The bootstrap script
downloads a portable copy and the exact source/tool revisions used by the
project.

## Quick start

1. Clone this repository.
2. Put the clean Japanese ISO at
   `input/jp/Boku_JP.iso`. See [input/README.md](input/README.md).
3. Run `install.bat`. It downloads dependencies, applies the public Spanish
   v1.0 patch locally, extracts the required data, and builds the plugin.
4. Run `launch-dev.bat`.
5. Once gameplay dialogue is visible, press **F7** to switch languages.

Neither input ISO is modified in place. The generated Spanish image is written
to `input/es/Boku_ES.iso`; all generated or copyrighted material is ignored by
Git.

For manual commands, troubleshooting, savestate rules, and logs, read the
[user guide](docs/USER_GUIDE.md).

## Development

The build is split into reproducible stages:

```powershell
./scripts/bootstrap.ps1
./scripts/setup.ps1
./scripts/pipeline.ps1
./scripts/build.ps1
./scripts/deploy.ps1
```

Run the tests with:

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
```

Architecture and reverse-engineering evidence are documented in
[docs/architecture.md](docs/architecture.md),
[docs/boku-dialogue-format.md](docs/boku-dialogue-format.md), and
[docs/findings.md](docs/findings.md). The detailed research trail is retained
in [docs/HANDOFF.md](docs/HANDOFF.md).

## Legal and safety

You must supply your own game dump. Do not commit or publish ISOs, extracted
assets, generated dialogue/font blobs, logs, memory captures, savestates, or
third-party binaries. The project checks the expected clean Japanese ISO MD5
(`B4D363D59CB87E25AB76AFC5384CCA31`) before patching.

The original code in this repository is licensed under the [MIT License](LICENSE).
Downloaded projects and translation materials retain their own licenses and
copyrights.

## Credits and AI disclosure

The project was led and tested by **KendritPy** with substantial assistance
from **OpenAI Codex** in reverse-engineering analysis, implementation,
documentation, and test development. All AI-assisted changes were directed,
reviewed, and validated by the human maintainer. See
[CONTRIBUTORS.md](CONTRIBUTORS.md) for the explicit attribution.
