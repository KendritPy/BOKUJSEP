# Architecture

BokuLangToggle is a PPSSPP-compatible userspace PRX for `UCJS10038`. It runs on the Spanish v1.0 executable so the translation's renderer changes remain available, then substitutes the original Japanese dialogue only when requested.

## Offline data

The build pipeline extracts both editions, identifies dialogue structurally, pairs compatible JP/ES records, and emits a deterministic bilingual blob. Records retain the exact 16-bit word streams and control codes rather than round-tripping through decoded text.

The structural identity is based on the game container hierarchy (script/member/dialog/block/text element/run), not volatile RAM addresses. The blob also stores enough context to reject ambiguous translated streams and page-incompatible pairs.

## Runtime path

Spanish mode follows the translated executable normally. On the first language-toggle request the PRX lazily loads the bilingual data and Japanese atlas, verifies the expected executable signature, and installs the narrow dialogue hook.

Japanese mode:

1. resolves the currently observed Spanish stream against the bilingual map;
2. substitutes the paired original Japanese stream;
3. swaps in the original Japanese font atlas;
4. changes the translated proportional-width load to the original 16-pixel fixed advance.

Returning to Spanish restores the translated stream, atlas, and proportional layout.

Unknown revisions, unresolved records, ambiguous matches, or incompatible pagination fail closed to Spanish. The plugin never intentionally renders a Spanish stream under the Japanese atlas.

## Input bridge

PPSSPP does not expose the chosen host F7 key directly to the guest. `tools/ppsspp_debug.py` uses PPSSPP's debugger interface to translate the host hotkey into the PSP Note-button bit. The PRX detects that edge and toggles the language. This keeps the implementation compatible with the stock audited PPSSPP build rather than requiring an emulator fork.

## Build layout

- `plugin/` — guest PRX source and configuration.
- `tools/` — extraction, comparison, bilingual-blob generation, font audit, and PPSSPP debugger bridge.
- `scripts/` — dependency bootstrap, local patch setup, build, deployment, and launcher automation.
- `tests/` — deterministic tests for the supported tooling.

See [boku-dialogue-format.md](boku-dialogue-format.md) for the serialized dialogue format and [findings.md](findings.md) for the verified reverse-engineering results that constrain the implementation.
