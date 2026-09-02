# User guide

## Installation

1. Install Git and Python 3.10 or newer.
2. Clone the repository.
3. Copy a clean Japanese `UCJS10038` ISO to `input/jp/Boku_JP.iso`.
4. Run `install.bat`.
5. Run `launch.bat`.

`install.bat` downloads pinned dependencies, applies the public Spanish v1.0 patch locally, extracts the required data, and builds the plugin. It does not modify the Japanese source image.

## Playing

- Press **F7** while gameplay dialogue is visible to toggle Japanese/Spanish.
- Menus and cinematics remain Spanish.
- Unresolved or incompatible dialogue automatically stays in or falls back to Spanish.
- The first switch can take slightly longer because runtime assets are loaded lazily.

## Savestates

PPSSPP savestates include plugin memory. Use a savestate only with the exact same `BokuLangToggle.prx` build that created it. After rebuilding the plugin, boot normally and create a fresh savestate. In-game saves are preferred for long-term progress.

## Development commands

| Command | Purpose |
| --- | --- |
| `install.bat` | Complete first-time setup and build |
| `./scripts/build.ps1` | Rebuild after source changes |
| `./scripts/deploy.ps1` | Copy the current build into portable PPSSPP |
| `launch.bat` | Deploy, launch PPSSPP, and enable the F7 bridge |

## Troubleshooting

### The ISO is rejected

Use the clean Japanese `UCJS10038` release. Setup expects MD5 `B4D363D59CB87E25AB76AFC5384CCA31`. Prepatched or modified source images are not supported.

### F7 does nothing

Close PPSSPP completely and restart it with `launch.bat`. The launcher deploys the plugin, configures the audited PPSSPP debugger interface, and starts the host-side hotkey bridge.

### A savestate behaves incorrectly

It was probably created with another plugin build. Restart the game, load an in-game save, and create a new PPSSPP savestate.

### Logs

The plugin log is written under:

```text
external/ppsspp-bin/portable/memstick/PSP/PLUGINS/BokuLangToggle/
```

For bug reports, include the PPSSPP version, plugin build hash, reproduction steps, relevant log excerpt, language mode, and a screenshot. Do not attach an ISO, savestate, or extracted copyrighted asset.
