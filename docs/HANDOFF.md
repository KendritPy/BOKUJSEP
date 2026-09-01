# Fresh-context handoff

Canonical compact state for **BokuLangToggle**. Read specialist docs only when
the current task needs them; do not reconstruct old assumptions from chat.

## Objective and operating rule

Build a PPSSPP-compatible userspace PRX for **Boku no Natsuyasumi Portable**
(`UCJS10038`) that toggles the genuine original Japanese and the curated
TraduSquare/GriffithVIII Spanish v1.0 translation at runtime, ideally redrawing
the already-visible textbox without advancing/restarting/changing saves.

Keep the **Spanish v1.0 executable as runtime base** unless evidence proves a
better design: it already supplies horizontal dialogue, VWF, widened layouts,
graphics and added subtitle paths. Preferred final architecture remains:
structural JP/ES raw streams -> verified whole-dialogue parser/lookup boundary
-> PSPModBase PRX. Do not fork PPSSPP unless the PRX path is actually blocked.

**USER INTERACTION RULE:** if a step requires playing the game, changing or
reading a textbox, pressing a game control, loading a save/state, or visually
checking PPSSPP, ask the user for the exact action, then **STOP AND WAIT** for
the returned log/JSON/screenshot/result. Do not try to keep “playing” the game
from the agent side; that tends to create loops and invented observations.

## Audited refs

| Source | Ref |
|---|---|
| Spanish release | `v1.0` -> `c0e3d2d5417013e4f4b34e416b58743f7efd86ad` |
| Korean tools | `v0.1.3-image-kr` / `97d0b30391ccfd44764863b1873f7d0a68246c96` |
| Pleonex + GriffithVIII | `dae1215b13ca7dbc6fa17971ecd3d58de86b097a` |
| PPSSPP 1.20.4 | `fa50bb1976065c4f8b1b47af227d367fe9771555` |

Pleonex default `master` misses the useful 2021 Yarhl work and GriffithVIII's
extended table/second font sheet. Never use newer PPSSPP `master` to define
1.20.4 debugger behavior.

## Settled work — do not redo

- Exact PPSSPP 1.20.4 debugger audit is complete:
  [ppsspp-1.20.4-debugger.md](ppsspp-1.20.4-debugger.md).
- `tools/ppsspp_debug.py` is the unified event-safe transport; unrelated
  broadcasts survive ticketed requests and raw reads default to
  `memory.read(replacements=false)`.
- 1.20.4 memcheck stop = unsolicited **`cpu.stepping`** with
  `reason="memory.breakpoint"` + `relatedAddress`; there is no
  `cpu.breakpoint.hit` event.
- Valid write-change memcheck = `write=true, change=true`.
- Interpreter flag = `-i`; broadcast config event = `broadcast.config.set`.
- Tests cover event interleaving/raw reads and 1.20.4/newer stepping payloads.
- Static archive/dialogue/font audit is complete:
  [boku-dialogue-format.md](boku-dialogue-format.md).
- Public Spanish-patch archaeology is complete. Official repo/release exposes
  no translation DB, assembly, build scripts or EBOOT map; useful public
  GriffithVIII/Pleonex lineage is documented in
  [spanish-patch-archaeology.md](spanish-patch-archaeology.md).
- Broad live-hook/tool search is complete. Recommendation: **LunaTranslator /
  LunaHook for discovery**, then the existing PSPModBase PRX for shipping;
  **TF-MultiFix** is the best MIT PRX implementation reference. Do not repeat a
  generic tool survey before new evidence. See
  [runtime-tool-survey.md](runtime-tool-survey.md).

After code changes run:

```bash
python -m unittest discover -s tests -v
python -m py_compile tools/ppsspp_debug.py tools/dialogue_watch_event_probe.py
git diff --check
```

## Current factual boundary

Static dialogue path:

```text
map/gz/*.bin -> named pack -> gzip/gzx -> unnamed pack -> member 1
             -> block -> 16-bit LE text run
```

Target durable identity:
`(script, named-pack member, dialog/block ID, text element, segment/run)`.
Preserve raw streams/control words (`8000`/`FFFF`, `8001`, `8002 arg`, and
context-sensitive `0000`); the tested page form `8002 hhhh 0000` must survive.
Korean evidence shows relocating inner dialogue members can cause crashes or
asset corruption, so do not repack CDIMG at runtime.

Runtime findings:

- Visible Spanish line was not found as literal UTF/Latin or a simple
  contiguous unknown 8/16-bit string.
- `0x0881Cxxx` was a false lead caused by PPSSPP replacement/emuhack views.
- `0x0892EC00` is rejected as dialogue identity: noisy time/render state; a
  prior writer path reached `sceKernelGetSystemTimeLow`.
- Corrected 32 MiB differential (`replacements=false`) left only 12 clean
  line-specific bytes and no changed RAM pointers.
- Best current **trace seed**, not hook: `0x0892EBA4`, size 2. It stayed stable
  within each sampled textbox and changed `0x0063 -> 0x01C0` across two lines.
  Nearby halfword patterns may be renderer/layout data; that role is unproved.

No parser, current-line object, font pointer or safe hook address is accepted.
See [findings.md](findings.md) and [addresses.md](addresses.md).

## Next runtime work

### A. Try Luna first

When user interaction is available, ask the user to attach LunaTranslator to
PPSSPP at a known dialogue and advance one textbox. Capture any stable hook
code, guest PC/address, register/offset, encoding and raw samples for two lines.
Cross-check the guest address with this repo. Luna is a hook finder/observable
text feed, **not proof of in-game write-back**. If it yields only OCR/glyph
noise, abandon that route and continue B.

### B. Authoritative writer trace

```text
launch-debug.bat
probe-watch-glyph.bat
```

This watches `0x0892EBA4`, size 2, under interpreter. Confirm the installed
memcheck is `write=true, change=true`. Accept only a 1.20.4 `cpu.stepping` stop
with `reason=memory.breakpoint` and matching `relatedAddress`. Capture writer
PC, pre-store GPRs, backtrace, disassembly, module map and hit count; trace
**backward** toward a whole-dialogue parser/lookup. Do not hook the renderer
seed itself. If the value changes but the watch does not fire, debug the
instrumentation before inventing another game address.

## Remaining unknowns

- Spanish code/glyph table; whether Spanish font assets still cover original JP
  glyphs.
- Exact JP->ES EBOOT code/data diff and injected code/segments.
- Stable runtime parser/lookup/current-line identity.
- Best whole-stream substitution boundary (resource, record, parser input, etc.).
- How to force the current visible textbox to rebuild immediately on toggle.

The Spanish table/EBOOT diff require the user's lawful JP + patched ISO or their
extracted data. Current ES text decoded through the JP table is not authoritative.

## Final PRX constraints

Prefer whole raw 16-bit stream substitution over per-glyph hooks. Generate an
immutable bilingual blob offline and retain the Spanish renderer. Any installed
hook must be edition-specific, signature-checked, bounds-checked and fail closed.
The current PRX is only milestone-zero loader/input: host F7 -> PPSSPP Note
button -> guest Note bit -> PRX language-state edge toggle. Dialogue replacement
is not implemented yet.

## Do not repeat

- No newer PPSSPP semantics for the 1.20.4 binary.
- No `cpu.breakpoint.hit`, `client.config.set`, `--cpu=interpreter`, or
  `game.status.paused` as stepping state.
- No `change=true` without `write=true`.
- No forensic RAM/code reads with `replacements=true`.
- No Spanish decoding through JP table presented as valid Spanish.
- No renderer/RAM address used as durable dialogue identity without evidence.
- No relocation of inner dialogue members just to fit text.
- No claim that the public Spanish repo contains its private build source.
- No claim that Luna extraction/overlay proves write-back.

## Deeper references

- `docs/ppsspp-1.20.4-debugger.md` — exact debugger semantics.
- `docs/boku-dialogue-format.md` — formats, controls, fonts, rebuild invariants.
- `docs/spanish-patch-archaeology.md` — Spanish/public tool lineage.
- `docs/runtime-tool-survey.md` — Luna/TF-MultiFix/other live-hook decision.
- `docs/findings.md` — chronological runtime evidence and rejected leads.
- `docs/architecture.md`, `docs/test-matrix.md` — target design/acceptance.
