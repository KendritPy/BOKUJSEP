# BokuLangToggle

BokuLangToggle is a PPSSPP plugin for **Boku no Natsuyasumi Portable** (`UCJS10038`) that switches gameplay dialogue between the original Japanese text and the TraduSquare/GriffithVIII Spanish v1.0 translation at runtime.

Press **F7** while a gameplay dialogue box is visible to toggle languages. Japanese mode restores the paired original text, Japanese font atlas, and fixed-width layout; Spanish mode restores the translated text and proportional layout. Menus and cinematics remain Spanish.

The repository contains source code and reproducible build tooling only. It does **not** include game images, extracted game assets, Sony software, or the Spanish translation patch.

## Status

- Runtime Japanese/Spanish switching for mapped gameplay dialogue.
- 8,539 structurally paired dialogue records.
- Automatic Spanish fallback when a record cannot be resolved safely or has incompatible pagination.
- One-command setup of the audited PPSSPP 1.20.4 Windows x64 environment.
- Savestates work when created with the same plugin build; rebuilds require a fresh savestate.

## Requirements

- Windows 10 or 11
- Git
- PowerShell 5.1 or newer
- Python 3.10 or newer
- A clean Japanese `UCJS10038` ISO
- Internet access during the initial setup

## Quick start

1. Clone this repository.
2. Put your clean Japanese ISO at `input/jp/Boku_JP.iso`.
3. Run `install.bat`.
4. Run `launch.bat`.
5. During gameplay dialogue, press **F7** to switch languages.

`install.bat` downloads the pinned dependencies, applies the public Spanish v1.0 patch locally, extracts the required data, builds the bilingual mapping, and compiles the plugin. The Japanese source image is never modified in place.

The generated Spanish image is written to `input/es/Boku_ES.iso`. Generated data, game images, external tools, logs, and build output are ignored by Git.

For troubleshooting and savestate rules, see [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## How it works

The plugin runs on the Spanish v1.0 executable and keeps its renderer improvements. Offline tooling pairs Japanese and Spanish dialogue by structural identity and builds an immutable bilingual blob from the exact 16-bit word streams.

At runtime the PRX intercepts the verified dialogue path. Spanish mode leaves the normal translated path unchanged. Japanese mode substitutes the paired original stream, swaps the original Japanese atlas into place, and restores the original fixed-width 16-pixel advance. Unknown or incompatible records fail closed to Spanish.

The F7 bridge uses PPSSPP's debugger interface to expose an otherwise-unused PSP Note-button input to the guest plugin; no custom PPSSPP build is required.

Technical details are in [docs/architecture.md](docs/architecture.md), [docs/boku-dialogue-format.md](docs/boku-dialogue-format.md), and [docs/findings.md](docs/findings.md).

## Development

The build stages can be run independently:

```powershell
./scripts/bootstrap.ps1
./scripts/setup.ps1
./scripts/pipeline.ps1
./scripts/build.ps1
./scripts/deploy.ps1
```

Run the test suite with:

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

## Legal

You must supply your own game dump. Do not commit or publish ISOs, extracted assets, generated dialogue/font blobs, memory captures, savestates, or third-party binaries.

Setup verifies the expected clean Japanese ISO MD5 (`B4D363D59CB87E25AB76AFC5384CCA31`) before patching.

The original code in this repository is licensed under the [MIT License](LICENSE). Downloaded projects and translation materials retain their own licenses and copyrights.

The Spanish translation is the work of TraduSquare/GriffithVIII and its credited contributors. BokuLangToggle is an independent compatibility layer and does not redistribute that translation.
