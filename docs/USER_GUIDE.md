# User guide

## Installation

1. Install Git and Python 3.10 or newer.
2. Clone the repository.
3. Copy a clean Japanese `UCJS10038` ISO to `input/jp/Boku_JP.iso`.
4. Run `install.bat`.
5. Run `launch.bat`.

`install.bat` downloads pinned dependencies, applies the public Spanish v1.0 patch locally, extracts the required data, and builds the plugin. It does not modify the Japanese source image.

## Playing

- Press **F7** to toggle Japanese/Spanish, including between gameplay dialogues.
- Japanese mode remains active across scene changes and later dialogues until you press the toggle again.
- To use a joystick button, map it in PPSSPP to the configured PSP control. The default is `NOTE`; edit `plugin/BokuLangToggle.ini` and change `ToggleButton` if you need another PSP control. Spare joystick buttons can use PPSSPP's `L2`, `L3`, `R2`, or `R3` controls.
- Menus and cinematics remain Spanish.
- An unresolved dialogue call may render temporarily in Spanish for safety, but the selected Japanese mode is preserved and the next dialogue is retried automatically.
- The first switch can take slightly longer because runtime assets are loaded lazily.

### Map a joystick button

1. Open PPSSPP **Settings → Controls → Control mapping**.
2. Find **Note**, select its mapping, and press the joystick button you want to use. Keep `ToggleButton=NOTE` in `plugin/BokuLangToggle.ini` for this option. F7 continues to work too.
3. Alternatively, set `ToggleButton=R3` and map **Dev-kit R3** to your desired button (or use L2, L3, or R2). Restart with `launch.bat` after changing the INI.

Use an otherwise unused PSP control to avoid triggering a game action at the same time. The physical button can be any button PPSSPP recognizes. Set `DefaultLanguage=JP` in the same INI if you want Japanese selected on a fresh boot.

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

The bridge writes `build/logs/hotkey.log`, including F7 detection, debugger acknowledgements, and connection failures. It reconnects automatically after a lost connection; press the key again after reconnection. It never replays a failed toggle because the first press may already have reached the game.

The plugin log identifies its compile date/time and records the observed and expected hook instructions, accepted language changes, and dialogue render state. `0=ES`, `1=JP`, and `2=font failure` in the **dialogue render** line. An acknowledged bridge input only confirms delivery to PPSSPP; look for **guest NOTE toggle edge received** and **language ES -> JP** in the plugin log to confirm the plugin applied it.

### A savestate behaves incorrectly

It was probably created with another plugin build. Restart the game, load an in-game save, and create a new PPSSPP savestate.

### Logs

The plugin log is written under:

```text
external/ppsspp-bin/portable/memstick/PSP/PLUGINS/BokuLangToggle/
```

For bug reports, include the PPSSPP version, plugin build hash, reproduction steps, relevant log excerpt, language mode, and a screenshot. Do not attach an ISO, savestate, or extracted copyrighted asset.
