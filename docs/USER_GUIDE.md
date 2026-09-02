# User guide

## Installation

1. Install Git and Python 3.10 or newer.
2. Clone the repository.
3. Copy your clean Japanese `UCJS10038` ISO to `input/jp/Boku_JP.iso` and your
   independently patched GriffithVIII/TraduSquare Spanish v1.0 ISO to
   `input/es/Boku_ES.iso`.
4. Run `install.bat` and wait for all stages to complete.
5. Run `launch-dev.bat` to start the supplied Spanish ISO in the audited
   portable PPSSPP 1.20.4 build.

`install.bat` validates both supplied images, bootstraps development
dependencies, runs the extraction/analysis pipeline, and builds the PRX. It
does not download the Spanish patch or modify either image.

## Playing

- Press **F7** while a gameplay dialogue box is visible to toggle Japanese or
  Spanish.
- Menus and cinematics intentionally remain Spanish.
- If a dialogue has incompatible pagination or cannot be identified, the
  plugin stays in or returns to Spanish instead of rendering unsafe Japanese.
- The first F7 switch may take a moment because the plugin lazily loads and
  resolves its runtime assets.

## Savestates

PPSSPP savestates include plugin memory. Use a savestate only with the exact
same `BokuLangToggle.prx` build that created it. After rebuilding the plugin,
boot normally and create a fresh savestate. In-game saves are the preferred
long-term saves and are not subject to this restriction.

## Useful commands

| Command | Purpose |
| --- | --- |
| `install.bat` | Complete first-time setup and build |
| `build.bat` | Rebuild the plugin after source changes |
| `deploy.bat` | Copy the current build into portable PPSSPP |
| `launch-dev.bat` | Deploy and launch the Spanish runtime with F7 enabled |

Reverse-engineering utilities remain available as Python modules under
`tools/`; they are intentionally not exposed as normal player launchers.

## Troubleshooting

### The ISO is rejected during setup

Confirm that the Japanese image is clean `UCJS10038` with MD5
`B4D363D59CB87E25AB76AFC5384CCA31`, and that the Spanish image is the official
v1.0 patched build with SHA-256
`3F3ED57C390684F774432B689EA94DF9C0EA5641D2ED907A3EE03BF1F69EE9C8`.

### F7 does nothing

Close PPSSPP completely and start it through `launch-dev.bat`. This launcher
deploys the plugin, enables PPSSPP plugins/debugging, and starts the host F7
bridge. F7 is intended for visible gameplay dialogue, not menus.

### The game behaves strangely after loading a state

The state was probably created with another plugin build. Restart the game,
load an in-game save, and create a new PPSSPP state.

### Logs

The deployed plugin log is under the portable PPSSPP memstick at:

```text
external/ppsspp-bin/portable/memstick/PSP/PLUGINS/BokuLangToggle/
```

When reporting a bug, include the plugin log, the exact action that triggered
it, whether Japanese or Spanish mode was active, and a screenshot. Do not
attach an ISO, savestate, or extracted copyrighted asset.
