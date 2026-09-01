# Fresh-context handoff

Read this first. It is the compact current state of **BokuLangToggle**. Detailed
evidence is in the linked docs; do not reconstruct old assumptions from chat
history.

## Goal

Build a PPSSPP-compatible userspace PRX for **Boku no Natsuyasumi Portable**
(`UCJS10038`) that switches between the original Japanese and the curated
TraduSquare/GriffithVIII Spanish v1.0 translation at runtime, ideally redrawing
the current textbox immediately without advancing, restarting, or changing
saves.

Use the **Spanish v1.0 executable as the runtime base** unless strong evidence
shows a better architecture. It already contains the useful horizontal-text,
VWF, widened-layout, graphics, and added-subtitle work. The intended final path
is still: structural JP/ES data -> verified parser/lookup hook -> existing
PSPModBase PRX. Do not fork PPSSPP unless the PRX route is actually blocked.

**Interaction rule:** if progress requires playing the game, changing a
textbox, pressing a game control, loading a save/state, or visually checking
PPSSPP, ask the user for that exact action, then **stop and wait** for the user
to return the log/JSON/screenshot/result. Do not try to simulate or repeatedly
"play" the game yourself; that tends to create loops and bad assumptions.

## Audited baseline

| Source | Pinned/audited ref | Use |
|---|---|---|
| Spanish release | `v1.0` -> `c0e3d2d5417013e4f4b34e416b58743f7efd86ad` | Runtime base/release claims; public repo has no build source |
| Korean project | `v0.1.3-image-kr` / `97d0b30391ccfd44764863b1873f7d0a68246c96` | Best public extract/rebuild/font/fixed-slot evidence |
| Pleonex + GriffithVIII | `dae1215b13ca7dbc6fa17971ecd3d58de86b097a` | Yarhl/PO rewrite + GriffithVIII extended table + second font sheet |
| PPSSPP | `v1.20.4` -> `fa50bb1976065c4f8b1b47af227d367fe9771555` | Exact debugger/runtime semantics |

Do not substitute newer PPSSPP `master` behavior for 1.20.4. Do not clone only
Pleonex `master`: it misses the useful 2021/GriffithVIII work.

## Already solved / do not redo

- Exact PPSSPP 1.20.4 debugger audit is complete. See
  [ppsspp-1.20.4-debugger.md](ppsspp-1.20.4-debugger.md).
- `tools/ppsspp_debug.py` is the unified transport: it preserves interleaved
  broadcasts/tickets, restores socket timeouts, and defaults raw reads to
  `memory.read(replacements=false)`.
- PPSSPP 1.20.4 memcheck stops are **`cpu.stepping` broadcasts**, not
  `cpu.breakpoint.hit`. Match `reason="memory.breakpoint"` and
  `relatedAddress=<watch start>`.
- A valid write-on-change memcheck needs `write=true, change=true`.
- Interpreter launch for 1.20.4 is `-i`, not `--cpu=interpreter`.
- Broadcast configuration is `broadcast.config.set`, not `client.config.set`.
- Unit tests exist for debugger message interleaving/raw reads and both old/new
  stepping payloads.
- Static archive/dialogue/font-format audit is complete. See
  [boku-dialogue-format.md](boku-dialogue-format.md).
- Public Spanish-patch/tool archaeology is complete. The official Spanish repo
  and release do **not** expose its translation DB, assembly patches, build
  scripts, or EBOOT map. Public GriffithVIII/Pleonex lineage was recovered and
  documented in [spanish-patch-archaeology.md](spanish-patch-archaeology.md).
- Broad runtime-tool research is complete. Do not repeat another generic tool
  search before obtaining new runtime evidence. See
  [runtime-tool-survey.md](runtime-tool-survey.md).

Verification after code changes:

```bash
python -m unittest discover -s tests -v
python -m py_compile tools/ppsspp_debug.py tools/dialogue_watch_event_probe.py
git diff --check
```

## Static data facts that matter

Dialogue path is roughly:

```text
map/gz/*.bin -> named pack -> gzip/gzx member -> unnamed pack -> member 1
             -> dialogue block -> 16-bit LE text runs
```

Use a structural identity, not RAM addresses:

```text
(script, named-pack member, dialog/block ID, text element, segment/run)
```

Known words include `0x8000`/`0xFFFF` terminators, `0x8001` newline,
`0x8002` page/pause + argument, and context-sensitive `0x0000`. Preserve the
source raw stream exactly; especially keep tested `8002 hhhh 0000` page guards.

The Korean project also demonstrates that relocating inner dialogue members can
cause crashes/corruption. Prefer immutable offline JP/ES blobs and fixed runtime
structures; do not repack CDIMG at runtime.

The **Spanish character table is still unknown**. Current ES decoded text that
uses the JP table is not authoritative. The exact JP->ES EBOOT diff and Spanish
font/code mapping require the user's lawful JP and patched ISO/extracted data.

## Runtime evidence and current boundary

Do not promote any of these addresses to a final hook yet.

- Literal UTF-8/Latin-1/UTF-16 and simple contiguous unknown 8/16-bit searches
  did not find the visible Spanish line.
- `0x0881Cxxx` was a false lead caused by PPSSPP replacement/emuhack views when
  RAM was read with `replacements=true`; it disappeared after raw reads.
- `0x0892EC00` is rejected as dialogue identity: it is noisy/time-driven render
  state and a prior writer path reached `sceKernelGetSystemTimeLow`.
- With corrected raw reads, a 32 MiB multi-sample differential left only 12
  clean line-specific bytes and no changed RAM pointers.
- The best current trace seed is **`0x0892EBA4` (2 bytes)**. It was stable within
  repeated samples of each textbox and changed `0x0063 -> 0x01C0` between two
  textboxes. Nearby repeated halfwords suggest renderer/layout output, but that
  semantic label is still only a hypothesis.

No parser, current-line object, font pointer, or safe hook address is accepted.
See [findings.md](findings.md) and [addresses.md](addresses.md).

## Best next routes

### 1. LunaTranslator/LunaHook discovery first

This is currently the easiest high-value experiment. Luna has dedicated PPSSPP
JIT/guest-address hook support and may expose the parser boundary faster than
manual tracing. Treat it only as a **discovery/validation tool**; it has not
been shown to provide the final in-game write-back toggle.

When the user is available, ask them to attach Luna to PPSSPP at a known early
dialogue and advance one textbox. Record any stable hook code, guest PC/address,
register/offset, encoding, and raw samples for two lines. Cross-check the guest
address with this repo before accepting it. If Luna yields only OCR/glyph-level
noise, stop pursuing it and return to the debugger trace.

### 2. Corrected authoritative write trace

Fallback/current tracer:

```text
launch-debug.bat
probe-watch-glyph.bat
```

The probe watches `0x0892EBA4`, size 2, in interpreter mode and must show an
installed `write=true, change=true` memcheck. On 1.20.4, accept only a
`cpu.stepping` event with `reason=memory.breakpoint` and matching
`relatedAddress`. Capture writer PC, pre-store GPRs, backtrace, disassembly,
module map and hit count, then trace **backward** toward a dialogue
parser/lookup. `0x0892EBA4` itself is not the intended final hook.

If the value changes but the watch still does not fire, debug the memcheck/tool
semantics before inventing another game address.

## Final implementation guidance

Prefer hooking the narrowest verified point that receives/resolves a whole
16-bit dialogue stream or stable record identity. A renderer/glyph hook is a
last resort. Generate an immutable bilingual blob offline and select JP/ES raw
streams at runtime while retaining the Spanish renderer changes.

For PRX mechanics, **TF-MultiFix** is the best MIT reference found for
module-relative MIPS hooks, load callbacks, `minjector`, and cache flushing.
Keep this project's stricter edition hash/signature/bounds checks and fail
closed on mismatch.

The existing PRX is intentionally milestone-zero: loader + Note-button edge
detector. Host F7 -> PPSSPP `input.buttons.press(note)` -> PSP Note bit -> PRX
language state works as the input design; dialogue substitution is not yet
implemented.

## Known unknowns

- Spanish code/glyph table and whether its font still contains all needed JP
  glyphs.
- Exact JP/ES EBOOT code/data diff and injected segments/hooks.
- Stable runtime parser/lookup/current-line identity.
- Whether the best final substitution point is resource lookup, script record,
  parser input, or another whole-stream boundary.
- How to force an already-visible textbox to rebuild immediately after toggle.

## Do not repeat these mistakes

- Do not use newer PPSSPP source to infer 1.20.4 behavior.
- Do not wait for nonexistent 1.20.4 `cpu.breakpoint.hit`.
- Do not use `game.status.paused` as debugger stepping state.
- Do not use `change=true` without `write=true`.
- Do not read forensic executable/RAM evidence with `replacements=true`.
- Do not use `--cpu=interpreter`; 1.20.4 uses `-i`.
- Do not decode Spanish dialogue with the JP table and treat it as Spanish text.
- Do not treat renderer coordinates/RAM addresses as durable dialogue IDs.
- Do not relocate dialogue-pack members just to make text fit.
- Do not claim the public Spanish repository contains its private build source.
- Do not treat Luna extraction/overlay as proof of in-game write-back.

## Read deeper only when needed

- [ppsspp-1.20.4-debugger.md](ppsspp-1.20.4-debugger.md) — exact debugger and
  memcheck semantics.
- [boku-dialogue-format.md](boku-dialogue-format.md) — containers, controls,
  fonts, rebuild invariants.
- [spanish-patch-archaeology.md](spanish-patch-archaeology.md) — public Spanish
  lineage and what is/not recoverable.
- [runtime-tool-survey.md](runtime-tool-survey.md) — Luna/PSPModBase/TF-MultiFix
  decision and licensing.
- [findings.md](findings.md) — chronological measurements and rejected leads.
- [architecture.md](architecture.md) / [test-matrix.md](test-matrix.md) — target
  design and acceptance coverage.
