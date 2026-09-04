# Architecture

BokuLangToggle is a PPSSPP-compatible userspace PRX for `UCJS10038`. It runs on the Spanish v1.0 executable so the translation's renderer changes remain available, then substitutes the original Japanese dialogue only when requested.

## Offline data

The build pipeline extracts both editions, identifies dialogue structurally, pairs compatible JP/ES records, and emits a deterministic bilingual blob. Records retain the exact 16-bit word streams and control codes rather than round-tripping through decoded text.

The structural identity is based on the game container hierarchy (script/member/dialog/block/text element/run), not volatile RAM addresses. The blob also stores enough context to reject ambiguous translated streams and page-incompatible pairs.

## Runtime path

Spanish mode follows the translated executable normally. At startup the PRX verifies the executable signature and installs the narrow dialogue hook. The first language-toggle request lazily loads the bilingual data and both font atlases, then verifies that the hook is still installed. With `DefaultLanguage=JP`, the input thread loads those assets automatically.

Japanese mode:

1. resolves the currently observed Spanish stream against the bilingual map;
2. substitutes the paired original Japanese stream;
3. swaps in the original Japanese font atlas;
4. changes the translated proportional-width load to the original 16-pixel fixed advance.

Returning to Spanish restores the translated stream, atlas, and proportional layout.

Unknown executable signatures remain fail-closed. An unresolved call uses the Spanish atlas without changing the selected language; the next resolved dialogue automatically uses Japanese again. The game thread applies the font alongside the selected stream, including when the toggle was pressed between dialogues. The font remains paired with the last rendered stream after the walker returns because GPU work can be deferred. Page-count mismatches use the matching page ordinal whenever the Japanese page exists.

Before validating the hook or width instruction, the plugin invalidates the relevant instruction-cache range. PPSSPP 1.20.4 uses `0x68xxxxxx` JIT markers in compiled code memory; invalidation restores the original instruction for strict signature checking (see `Core/HLE/sceKernel.cpp` and `Core/MIPS/JitCommon/JitBlockCache.cpp` in the audited source). Markers are never accepted as executable signatures.

Hook validation captures the call and width instructions before logging and compares those captured values. File I/O in logging can yield to the game thread, allowing JIT compilation to replace the live instruction again. Reading the call again after logging incorrectly rejected an already installed hook. The runtime log records both the snapshot and expected installed call to diagnose this separately from incompatible savestates.

## Input bridge

PPSSPP does not expose the chosen host F7 key directly to the guest. `tools/ppsspp_debug.py` uses PPSSPP's debugger interface to translate the host hotkey into the configured PSP control bit. The PRX detects that edge and toggles the language. Map any physical joystick button to the same PSP control in PPSSPP. This keeps the implementation compatible with the stock audited PPSSPP build rather than requiring an emulator fork.

The bridge waits for an input acknowledgement and holds the guest control for three frames to cover the plugin's polling interval. A rotating local log records connection and input events. Connection failures trigger reconnection without replaying a toggle whose delivery may already have succeeded.

## Build layout

- `plugin/` — guest PRX source and configuration.
- `tools/` — extraction, comparison, bilingual-blob generation, font audit, and PPSSPP debugger bridge.
- `scripts/` — dependency bootstrap, local patch setup, build, deployment, and launcher automation.
- `tests/` — deterministic tests for the supported tooling.

See [boku-dialogue-format.md](boku-dialogue-format.md) for the serialized dialogue format and [findings.md](findings.md) for the verified reverse-engineering results that constrain the implementation.
