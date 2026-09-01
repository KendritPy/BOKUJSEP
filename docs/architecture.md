# Architecture

The working hypothesis is a PPSSPP-compatible userspace PRX loaded only for
`UCJS10038`, running on the Spanish v1.0 executable. A persistent immutable
bilingual blob will map a measured structural dialogue identity to the exact
raw JP or ES 16-bit word stream. Substitution will occur at the narrowest
verified lookup/interpreter boundary, never at individual glyph level unless
runtime evidence rules out the safer hooks.

The intended identity is `(script, named-pack member, dialog/block ID, text
element, segment/run)`. This mirrors the public container structure and avoids
using volatile RAM addresses as content IDs. The offline builder must preserve
`0x8000` versus `0xFFFF` terminators, `0x8001` newlines, and the tested
`0x8002 argument 0x0000` page sequence exactly. See
`boku-dialogue-format.md`.

The host hotkey path is intentionally emulator-supported rather than a PPSSPP
fork: `F7 -> WebSocket input.buttons.press(note) -> sceCtrl guest state -> PRX
edge detector -> ToggleLanguage()`. The PSP Note bit is included in PPSSPP's
user input mask and is not a gameplay control used by Boku.

The milestone-zero PRX only logs startup and toggles internal state. Hook
installation is disabled until the Spanish EBOOT hash and instruction bytes
are known. Any future hook must verify its surrounding signature and fail
closed when it does not match.

The present runtime trace starts from the line-dependent renderer halfword at
`0x0892EBA4` and walks backward to a parser/lookup boundary. That halfword is
evidence for a writer path, not the proposed hook or a dialogue identity.
