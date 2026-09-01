# Architecture

The working hypothesis is a PPSSPP-compatible userspace PRX loaded only for
`UCJS10038`, running on the Spanish v1.0 executable. A persistent immutable
bilingual blob will map a measured structural dialogue identity to the exact
raw JP or ES 16-bit word stream. Substitution will occur at the narrowest
verified lookup/interpreter boundary, never at individual glyph level unless
runtime evidence rules out the safer hooks.

The host hotkey path is intentionally emulator-supported rather than a PPSSPP
fork: `F7 -> WebSocket input.buttons.press(note) -> sceCtrl guest state -> PRX
edge detector -> ToggleLanguage()`. The PSP Note bit is included in PPSSPP's
user input mask and is not a gameplay control used by Boku.

The milestone-zero PRX only logs startup and toggles internal state. Hook
installation is disabled until the Spanish EBOOT hash and instruction bytes
are known. Any future hook must verify its surrounding signature and fail
closed when it does not match.
