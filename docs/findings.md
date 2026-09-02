# Verified findings

This file records the reverse-engineering results that materially constrain the current implementation. Historical dead ends and one-off probe transcripts are intentionally omitted.

## Baseline

- Game: `Boku no Natsuyasumi Portable: Mushi Mushi Hakase to Teppen-yama no Himitsu!!`
- Product ID: `UCJS10038`
- Spanish translation: TraduSquare/GriffithVIII v1.0 (2025-08-01)
- Audited emulator: PPSSPP 1.20.4 Windows x64
- Expected clean Japanese ISO MD5: `B4D363D59CB87E25AB76AFC5384CCA31`

The Spanish patch keeps the original Japanese `BOOT.BIN` and replaces `EBOOT.BIN`. The Spanish executable is the runtime base because it contains the translation's horizontal-dialogue, subtitle, menu-layout, and variable-width-font changes.

## Dialogue data

The public Boku tooling lineage and direct JP/ES extraction agree on the game's nested CDIMG/pack/dialogue structure. Dialogue text is serialized as little-endian 16-bit words with controls including `0x8000`, `0xFFFF`, `0x8001`, and `0x8002` plus its argument and page guard.

The current pipeline structurally pairs 8,539 JP/ES dialogue records and stores the exact raw streams in a deterministic bilingual blob. Runtime lookup does not use volatile renderer addresses as dialogue identity.

See [boku-dialogue-format.md](boku-dialogue-format.md) for the format contract.

## Executable/runtime behavior

Static comparison showed that the Spanish executable adds an injected executable region and modifies the original text/render path. Earlier renderer-state candidates such as `0x0892EBA4` were experimentally rejected as dialogue identities; they represented geometry/layout state.

The working implementation instead hooks the verified whole-dialogue path. The plugin signature-checks the expected Spanish executable before installing that hook and fails closed on unknown revisions.

Japanese mode requires two renderer changes in addition to replacing the dialogue stream:

- restore the original Japanese font atlas;
- replace the Spanish proportional-width load with the original fixed 16-pixel cell advance.

Restoring broader Japanese text-walker differences was tested and rejected because it corrupted layout. The narrow width-state change is sufficient for the supported dialogue path.

## Ambiguity and pagination

A translated byte stream can correspond to more than one original Japanese record. The bilingual blob therefore stores structural/context information and marks ambiguous signatures rather than guessing.

JP and ES records can also differ in page count. The runtime resolver maps compatible page ordinals explicitly; incompatible records remain or fall back to Spanish.

These fail-closed rules are deliberate. A missing Japanese switch is preferable to drawing the wrong text or mixing Spanish text with the Japanese atlas.

## PPSSPP integration

PPSSPP's debugger interface is used only as a host input bridge: a host F7 press is translated to the PSP Note-button bit, which the PRX detects in guest input state. The mod therefore works with the audited stock PPSSPP build and does not require a custom emulator fork.

Savestates include plugin memory. They are safe only with the exact plugin build that created them; after rebuilding, boot normally and create a fresh savestate.
