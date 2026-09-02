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

The first reversible mixed-mode proof established the required render state:
Japanese mode swaps the original atlas 0 and uses the original raw JP stream,
while retaining the Spanish parser and changing only its injected proportional
width load at `0x0891B5D4` from `lb s6,0(a1)` to `li s6,0x10`. This produces
the original 16-pixel Japanese cell advance. Restoring the seven broader JP
text-walker differences is explicitly rejected because it corrupts layout.

`tools/build_dialogue_blob.py` now emits a deterministic, versioned immutable
blob from the structural pair map. It deduplicates raw streams, hashes the
entry table and payload, retains the full structural identity, and flags an ES
signature when that same translated byte stream maps to more than one JP raw
stream. Runtime text-only lookup must fail closed for those flagged entries
until loader context supplies the structural identity.

Blob v2 also stores the ES dialogue-file-relative text offset, a deduplicated
256-byte dialogue-file header signature, and a JP/ES page-count mismatch flag.
At runtime an ambiguous candidate can be checked by subtracting its text offset
from the live full-stream pointer and comparing that computed base with the
stored header. Page pointers after `0x8002 argument` target the following
`0x0000` guard; aligned JP/ES records must map page ordinal to page ordinal,
not reuse a byte offset from the other language.

The callsite must be signature-checked and patched during module startup, before
PPSSPP JIT-compiles that page and exposes internal `0x68xxxxxx` emuhack words to
guest-side reads. In ES mode the wrapper does no lookup. Runtime blob/font
allocation, atlas scanning and JP resolution remain deferred to the first F7
edge so startup stays allocation-neutral. Code writes explicitly flush data and
instruction caches; later toggles must not mistake JIT replacement words for
edition-signature failures.

Fail-closed behavior must cover render state as well as pointer lookup. Before
entering JP mode, the currently observed stream is resolved first; an
unresolved or page-count-incompatible stream refuses the toggle. If advancing
while already in JP mode reaches such a stream, the wrapper restores the ES
atlas and proportional-width instruction before drawing it, changes the global
mode back to ES, and logs the automatic fallback. Never render an ES stream
under the JP atlas.

The present runtime trace starts from the line-dependent renderer halfword at
`0x0892EBA4` and walks backward to a parser/lookup boundary. That halfword is
evidence for a writer path, not the proposed hook or a dialogue identity.
