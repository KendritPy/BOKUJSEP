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
- Former trace seed `0x0892EBA4` is now rejected as renderer geometry. It is
  not a hook candidate or durable dialogue identity.
- The first valid `write=true, change=true` interpreter run logged two exact
  `Write16(CPU)` accesses at `0x0892EBA4`, both with reported guest PC
  `0x088A0E4C`. PPSSPP immediately emitted `cpu.resume` rather than leaving a
  usable stepping stop, so pre-store registers/backtrace were not captured.
  The old report says `timeout`, but its saved MEMMAP events are real writer
  evidence. Treat `0x088A0E4C` as a trace lead, not yet a safe hook: the
  pristine instruction there disassembles as `lw v1, 8(a0)`, not a store.

The active textbox object for the proven dinner line was found at `0x08929CA4`;
its `+0x54` field points to the exact raw stream (`0x0D7513E0`). This object
location is volatile evidence, not a durable address. Nearby fields identify
the `msg` / `e_subtitle` resource class but do not expose a verified structural
script/block identity.

## Next runtime work

### A. Try Luna first

When user interaction is available, ask the user to attach LunaTranslator to
PPSSPP at a known dialogue and advance one textbox. Capture any stable hook
code, guest PC/address, register/offset, encoding and raw samples for two lines.
Cross-check the guest address with this repo. Luna is a hook finder/observable
text feed, **not proof of in-game write-back**. If it yields only OCR/glyph
noise, abandon that route and continue B.

Use `launch-luna.bat` for this experiment. It intentionally starts PPSSPP with
no ISO; attach Luna in HOOK mode first, then load `input/es/Boku_ES.iso` from
PPSSPP's File > Load menu. The normal `launch-dev.bat` still auto-loads the ISO.

This experiment is complete and rejected for whole-dialogue discovery. Luna
0.16.5.4 recognized PPSSPP 1.20.4 and `UCJS10038`, but built-in hooks were empty;
a controlled default search returned 1,676 resource/glyph-noise results and no
visible Spanish line. Do not repeat generic Luna searches or cycle encodings.

### B. Completed and rejected writer trace

```text
launch-debug.bat
probe-watch-glyph.bat
```

This experiment is complete. The eventual non-pausing interpreter log captured
the writer and proved the address is transformed renderer geometry. Retain the
probe as debugger tooling evidence, but do not rerun it as the next discovery
step and do not trace its callers toward dialogue code without independent text
evidence.

The probe now also records an exact matching PPSSPP MEMMAP `Write*(CPU)` log as
`logged_hit` when 1.20.4 resumes before the stepping broadcast can be consumed.
That fallback preserves the writer PC but labels later registers/backtrace as
post-hit and non-authoritative. Rerun it once to obtain a structured report;
then reconcile the logged PC with runtime disassembly before tracing callers.

A subsequent rerun changed the halfword `0x0095 -> 0x0084` but yielded four
rapid `cpu.resume` broadcasts and neither a stable stepping event nor a MEMMAP
log. The earlier log's reason was `CPU`, which is PPSSPP's JIT memcheck path,
not the interpreter's `interpret` path. `launch-dev.ps1` now refuses to start
while another PPSSPP process exists; close PPSSPP fully before
`launch-debug.bat` so a pre-existing JIT instance cannot absorb the launch and
silently defeat `-i`. Timeout reports now snapshot the final memcheck/hit count.

The next clean-launch run proved the user action and memcheck are valid:
`0x0892EBA4` changed `0x0136 -> 0x0084` and the installed memcheck's hit count
rose `0 -> 6`. Its event queue was dominated by high-rate analog-input
broadcasts and retained only four `cpu.resume` transitions, with no corresponding
stepping/log payload. The debugger transport now disables input/game broadcasts,
explicitly enables logger/stepping broadcasts, and records the effective
`broadcast.config.get` response. Do not ask the user to send the JSON; read
`analysis/debugger/dialogue-watch-glyph.json` directly after each run.

With broadcast noise removed, another run changed `0x0031 -> 0x0063` and the
memcheck rose `0 -> 4`, with exactly four `cpu.resume` broadcasts but still no
observable stop/log payload. The user action is conclusively correct; do not
repeat the pausing probe. `probe-watch-glyph.bat` now uses a non-pausing,
register-rich `logFormat` (`BOKU_WATCH`) so the MEMMAP event itself carries PC,
RA, SP and key GPRs without depending on the broken transient stepping state.

That log-only trace succeeded. `0x088A0E4C` is the real interpreter writer:
`sh v1,0x174(v0)` with `v0=0x0892EA30`, `v1=0x0053`, producing the exact
watched address/value. Live disassembly shows `z_un_088a0ccc` calculating
fixed-point transformed coordinates, writing adjacent halfwords and setting
render flags; callsites are `0x088A1150` and `0x088A1328`. Therefore
`0x0892EBA4` is conclusively rejected as renderer geometry. Do not hook or
trace it further. Log-only mode intentionally skips live backtrace/register
requests; authoritative pre-access registers are embedded in the log event.

### C. Completed and rejected: Spanish injected raw-stream walker

Offline ELF comparison found that the Spanish patch replaces the decrypted
Japanese executable with a same-size ELF and repurposes `.comment` as a WAX
`0x7F00`-byte injected region at guest `0x08918FF0..0x08920EF0`. Seven direct
patched edges enter it. At guest `0x08843070`, the exact Spanish signature is:

```text
move a0,s3
jal  0x08919BF0
```

The target walks 16-bit words and recognizes the established raw `0x8000`
terminator, but it is not the active path for the tested dinner dialogue.
`probe-stream.bat` did not hit for one transition. `probe-injected-edges.bat`
then signature-checked all seven original-text edges into the injected region
and none hit for the next transition. A CPU-log self-test at the known active
renderer writer hit immediately in the same JIT session, so this is a runtime
rejection, not an assumed debugger failure. Do not repeat these probes for this
scene.

The corrected Spanish text normalizer now treats the reused full-width U+300C
glyph as a separator. It identifies the known dinner lines as exact structural
records under `G2a.bin` / `M_G0120*.bin.gz`, dialog 4028: key `0122_12` for
`Muy bien, Boku. Has acertado!` and key `0122_09` for `La cena que he preparado
hoy era:`. Use the text currently visible in PPSSPP to select the next exact
record; old screenshot phrases are no longer resident after advancing.

## Remaining unknowns

- Spanish code/glyph table; whether Spanish font assets still cover original JP
  glyphs.
- Exact JP->ES EBOOT code/data diff and injected code/segments.
- Stable runtime parser/lookup/current-line identity.
- Best whole-stream substitution boundary (resource, record, parser input, etc.).
- How to force the current visible textbox to rebuild immediately on toggle.

## Completed reversible Japanese render proof

For `G2a.bin` / `M_G01200.bin.gz` / key `0122_12`, swapping the exact paired JP
raw stream plus original JP atlas 0 produced correct kana and kanji. The final
spacing repair retained the Spanish parser and patched only `0x0891B5D4` from
`0x80B60000` (`lb s6,0(a1)`) to `0x24160010` (`li s6,0x10`). The resulting
uniform 16-pixel advance is consistent with the original 16x16 atlas grid and
was visually confirmed with no overlap. The proof restored stream, atlas and
instruction signatures successfully.

The structural map contains 8,539 pairs. 8,131 records have an ES raw stream
that resolves to one JP stream by content alone; 408 records participate in 34
ambiguous ES raw values and must not be guessed. `tools/build_dialogue_blob.py`
generates the versioned, deduplicated bilingual blob and marks those records
ambiguous so the future runtime resolver can fail closed until loader context
provides their structural identity.

The subsequent two-stream context capture proved that multi-page advancement
changes the textbox object's stream field from the full ES stream at
`0x0D751EF8` to the second-page suffix at `0x0D751F48`, exactly `0x50` bytes
later and pointing at the preserved `0x0000` guard after `0x8002 0x002D`.
Therefore runtime substitution must map page ordinal, never cross-language byte
offset. JP/ES page counts align for 8,185 pairs and differ for 354; mismatches
must fail closed until the page-advance state is hooked.

For the baseline's four identical ES candidates, subtracting each structural
`text_offset` from `0x0D751EF8` and comparing the live dialogue-file header
resolved only `G2a.bin` pack 0 (`M_G01200.bin.gz`): base `0x0D749D00` matched
all 256 checked bytes and block count 40. The other candidates mismatched at
byte zero. Blob v2 stores this source-header context for runtime disambiguation.

The first general PRX build initially installed its wrapper at module start and
caused a black-screen boot stall because startup also exercises the walker.
The corrected build only validates assets/signatures at startup and installs
the wrapper lazily on F7. PPSSPP savestates serialize module/RAM state: loading
an old state made with an earlier BokuLangToggle restore that old PRX image and
logging behavior over the current build. Such a state cannot validate a new
PRX unless the plugin is reloaded afterward; use a normal in-game save/new game
or a debugger-side reversible proof for that historical scene.

The Spanish table/EBOOT diff require the user's lawful JP + patched ISO or their
extracted data. Current ES text decoded through the JP table is not authoritative.

## Final PRX constraints

Prefer whole raw 16-bit stream substitution over per-glyph hooks. Generate an
immutable bilingual blob offline and retain the Spanish renderer. Any installed
hook must be edition-specific, signature-checked, bounds-checked and fail closed.
The current PRX implements the complete host F7 -> PPSSPP Note -> guest edge ->
signature-checked whole-dialogue replacement path. It lazily resolves the live
Spanish stream against blob v2, swaps the paired Japanese stream/font/width,
and restores Spanish state on the next toggle. Unresolved or page-count-
incompatible records refuse Japanese mode or trigger automatic Spanish
fallback before rendering. The structural map contains 8,539 pairs; menus and
cinematics intentionally remain Spanish.

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
