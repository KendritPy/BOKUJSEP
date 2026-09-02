# Findings

## Baseline (2026-08-31)

- Target: `Boku no Natsuyasumi Portable: Mushi Mushi Hakase to Teppen-yama no Himitsu!!`.
- Expected product ID: `UCJS10038` (PARAM.SFO commonly formats this as `UCJS-10038`).
- Official Spanish translation release: v1.0, dated 2025-08-01.
- Spanish patch archive SHA-256: `F38EDCE9CFEAD315574460F9F0356AFF1B6EE03FD22AD023D09CA11B24F735F7`.
- Spanish xdelta SHA-256: `B6F4145FD880406CC56D9F3C929A56E642F0218EEBC03E9ECE84C3C9228074C3`.
- Known clean Japanese ISO MD5 from the Korean tool project: `B4D363D59CB87E25AB76AFC5384CCA31`.
- PPSSPP portable baseline: 1.20.4 Windows x64.
- PPSSPP ZIP SHA-256: `FBC9CD2F5131B159A92424E5C458C35CE43BA603CDDED64DFC98E4BD4F17FF93`.
- PPSSPP 1.20.4 source commit: `fa50bb1976065c4f8b1b47af227d367fe9771555`.
- Formerly referenced PPSSPP snapshot `56bba5f6f5e4ce5786f8528e73f2ece391fe34ea`
  is from 2026-08-31, more than three months after 1.20.4, and cannot define
  the shipped debugger protocol.
- Spanish release tag: `v1.0` -> `c0e3d2d5417013e4f4b34e416b58743f7efd86ad`.
  The current documentation-only `main` snapshot is
  `86820b58d881c9d947b87f6a913297bc9aec8163`.
- Korean tooling tag: `v0.1.3-image-kr` ->
  `97d0b30391ccfd44764863b1873f7d0a68246c96`.
- Pleonex/GriffithVIII tooling snapshot:
  `dae1215b13ca7dbc6fa17971ecd3d58de86b097a`. This includes Pleonex's
  non-default `feature/yarhl` rewrite plus GriffithVIII's extended table and
  second font sheet. The default branch's `c88677d...` snapshot is incomplete
  for this research.

## Local inventory

- No clean Japanese ISO, Spanish-patched ISO, prior PPSSPP installation, or save was found in the usual Desktop/Documents/Downloads/configuration locations.
- The official Spanish v1.0 patch and PPSSPP portable baseline were downloaded into ignored local directories.
- PSPModBase's Windows PSPSDK submodule is present, so PRX compilation requires no user-installed PSP toolchain.
- PPSSPP 1.20.4 persists remote-debugger activation through `[General]` keys in `ppsspp.ini`; the newer upstream `--debugger` command-line flag is not present in that release binary. Development scripts configure the release-supported INI path and back it up.

## Spanish patch scope

The official project documents 100% dialogue, graphics, insect names,
cinematics, minigames, save-data presentation, widened menus, and VWF. Its
EBOOT changes add horizontal dialogue and several subtitle systems. Therefore
the Spanish EBOOT is the initial runtime base; Japanese mode must restore
original Japanese content without discarding those useful renderer changes.

The public Spanish Git history contains only README/LICENSE/screenshots. The
release RAR contains `Leeme.txt`, `Parcheador.exe`, and a single xdelta. It does
not contain the translation database, build tools, assembly, or an EBOOT map.
See `spanish-patch-archaeology.md` for the audited public lineage and the clear
boundary between confirmed facts and inference.

## Static format/tool audit (2026-09-01)

- Pleonex's default `master` ends in 2015. The 2021 public `feature/yarhl`
  branch migrates to Yarhl and adds PO export; default shallow clones miss it.
- Two later GriffithVIII commits are still public by SHA: `dbf1d2f...` adds an
  extended, game-tested table and `dae1215...` adds the second font sheet.
- The Yarhl tool is an exporter, not a complete patch builder. It has no PO
  import/rebuild path, stops at every `0x0000`, and uses the old 1,024-entry
  embedded table.
- The Korean v0.1.3 project is the most complete public successor: extraction,
  raw/fixed-slot rebuilds, font/PIM2 patching, image patching, 8,526 structured
  dialogue rows, and checked-in stability reports.
- Its fixed-pack report records 59 changed scripts and 392 audited members with
  zero inner offset/size changes. A prior relocation of 12 members caused
  crashes or background corruption.
- Its pause-guard report establishes the tested multi-page sequence
  `8002 hhhh 0000`; removing the zero can consume the next page's first glyph.
- The old Pleonex wiki's `0x8000` CDIMG padding sentence is a typo. Its own FAT
  formula and both public implementations use `0x800`-byte sectors.
- GriffithVIII's public `PSP_ELFHandler` can add a loadable RWX segment to a PSP
  ELF, but no public evidence proves it built the Spanish EBOOT. Its README also
  omits the `INCREASE` verb required by the code.

## Runtime investigation (2026-08-31)

- Exact visible Spanish dialogue was not found in PSP RAM as literal UTF-8, Latin-1, UTF-16, or as a simple unknown fixed-width 8-bit/16-bit equality-pattern stream.
- A first two-sample RAM differential misleadingly concentrated line-transition changes around `0x0892EBDC-0x0892EC33`.
- A change watchpoint on `0x0892EC00-0x0892EC33` fired only ~0.00033 s after arming, before the user advanced dialogue.
- The hit PC was `0x0882AC2C`; the backtrace includes a call to `sceKernelGetSystemTimeLow`, and the watched region consists largely of repeated small 16-bit pairs. This is consistent with time-driven render/geometry state, not a current-dialogue identity structure.
- Therefore `0x0892EC00` is a **rejected dialogue-identity candidate**. It may still contain renderer/layout output and can be useful for tracing backward into the text pipeline.
- The first differential probe used only one same-line noise interval and was vulnerable to periodic-state aliasing. `dialogue_stable_diff_probe.py` now samples each textbox repeatedly at irregular intervals before classifying line-specific changes.
- PPSSPP `memory.read` defaults to exposing active replacement/emuhack instructions in executable memory. Full RAM differential probes must request `replacements=false`; otherwise PPSSPP's own runtime code substitutions can appear as false guest-memory changes.
- After switching debugger RAM reads to `replacements=false`, a fresh 32 MiB stable differential found only 12 line-specific clean bytes, zero changed RAM pointers, and the prior `0x0881Cxxx` executable-code cluster disappeared entirely. This validates that the earlier code-region candidates were debugger replacement contamination, not Boku self-modifying its EBOOT.
- A targeted rerun over the few surviving pages found a strong line-dependent cluster in page `0x0892EB00`. In that run `0x0892EBA4` was stable across all same-textbox samples and changed from little-endian halfword `0x0063` (99) on textbox A to `0x01C0` (448) on textbox B. Nearby halfwords change in repeated pairs, still consistent with renderer/layout geometry rather than raw dialogue identity.
- Differential candidates must be classified against PPSSPP's `hle.func.list` / module map before any watchpoint is armed. `classify_diff_candidates.py` performs this gate on saved differential reports.
- The original watch scripts incorrectly inferred a breakpoint hit from
  `cpu.status.stepping`. A source audit then found a second, opposite error:
  PPSSPP 1.20.4 has no `cpu.breakpoint.hit` event. It broadcasts
  `cpu.stepping` with `reason="memory.breakpoint"` and `relatedAddress` equal to
  the memcheck start. The prior event probe discarded that real notification
  as unrelated and resumed the CPU. `dialogue_watch_event_probe.py` now matches
  the exact 1.20.4 payload while also accepting newer enriched stepping events.
- A second watchpoint bug was found in the PPSSPP memory-breakpoint flags: `change=true` is `MEMCHECK_WRITE_ONCHANGE`, but PPSSPP's write-change path requires the normal `MEMCHECK_WRITE` bit as well. The previous probe used `write=false, change=true`, an inert/invalid combination. The probe now uses `write=true, change=true` and verifies the installed memcheck via `memory.breakpoint.list` before proceeding.
- In 1.20.4 interpreter mode, `WRITE_ONCHANGE` does not compare the pending
  value with RAM; the interpreter calls `ExecMemCheck()`, which treats it as a
  normal write watch. The JIT path calls `ExecOpMemCheck()` and performs the
  supported-store value comparison. Interpreter mode is still preferable for
  finding the writer because it stops before executing the store with the
  writer PC and pre-store registers intact.
- `probe-watch-glyph.bat` now watches the exact 2-byte halfword at `0x0892EBA4`, which is proven by the corrected targeted differential to change between the two tested textboxes. The goal is to catch the actual CPU instruction that updates line-dependent renderer/layout data and then trace backward toward the text parser.
- The non-pausing interpreter trace finally captured that writer reliably. At
  `0x088A0E4C`, `z_un_088a0ccc` executes `sh v1,0x174(v0)` with
  `v0=0x0892EA30` and `v1=0x0053`, exactly producing address `0x0892EBA4` and
  the observed after-value. The surrounding function calculates fixed-point
  transformed values and stores adjacent halfword coordinates plus render
  flags. Its callers are at `0x088A1150` and `0x088A1328`. This conclusively
  classifies the seed as renderer geometry, not a dialogue parser, lookup, or
  durable current-line identity. Do not trace or hook it further.
- LunaTranslator 0.16.5.4 was attached to PPSSPP before game load and correctly
  recognized PPSSPP 1.20.4 plus `UCJS10038`. Its built-in hooks produced no
  text stream. A default hook search created 3,959 active candidates and 1,676
  results after one controlled textbox transition, but only resource/glyph
  noise; neither `Muy bien` nor `Boku` appeared even after disabling the
  pure-English/unordered filters. Luna is rejected for this patched executable's
  whole-dialogue discovery path.
- The clean executable comparison is now authoritative: Spanish `EBOOT.BIN`
  and Japanese `BOOT.BIN` are decrypted ELFs of the same size. The Spanish ISO
  leaves its `BOOT.BIN` byte-identical to Japanese and replaces `EBOOT.BIN`.
  The patch converts the original non-alloc `.comment` payload into a writable,
  allocatable, executable `0x7F00`-byte region at module offsets
  `0x00114FF0..0x0011CEF0` (guest `0x08918FF0..0x08920EF0`), shifts `.data` by
  `0x7F00`, changes 1,436 `.text` bytes / 562 instruction words, and introduces
  seven direct branches from original `.text` into the injected region.
- The strongest static injected edge is guest `0x08843074 -> 0x08919BF0`. Immediately
  before it, `0x08843070` executes `move a0,s3`. The injected function reads
  16-bit words from that pointer, recognizes `0x8000`, and walks/counts the raw
  stream. Although this matches the established serialization, a verified
  log-only breakpoint at this site did not execute during one controlled
  textbox transition. A second probe signature-checked and watched all seven
  original-text edges into the injected region; none executed during the next
  transition. A self-test at the active renderer writer produced a JIT CPU-log
  event immediately, proving that CPU logpoints work in the current emulator
  session. Therefore the injected edges are rejected for this scene's active
  dialogue path rather than blamed on debugger transport.
- Correcting normalization for the Spanish patch's reused U+300C separator
  located the canonical visible records precisely. `Muy bien, Boku. Has
  acertado!` is ES record 4978 (also structural duplicates 5017/5038/8093),
  `G2a.bin`, `M_G01200.bin.gz`, dialog 4028, block 35, element 4, key
  `0122_12`. `La cena que he preparado hoy era:` is record 4993 (plus three
  duplicates), the same script/dialog and key `0122_09`. Neither exact raw
  stream nor several 16-24 byte interior windows were resident in the current
  32 MiB RAM snapshot after the scene had advanced, so tracing must be armed
  against the textbox actually visible rather than an older screenshot.
- JIT memcheck register snapshots contained many `0xDEADBEEF` values. Future memory-breakpoint work should use PPSSPP interpreter mode (`launch-debug.bat`) for reliable registers/memchecks.
- The old launcher passed unsupported `--cpu=interpreter`. PPSSPP 1.20.4's
  desktop parser selects the interpreter with `-i`; `launch-debug.bat` now
  reaches that supported path.

## Pending measured results

Input hashes, detected IDs, per-file diffs, font coverage, decrypted EBOOT
hashes, and verified runtime text/parser addresses will be appended by the pipeline/debugging tools as evidence is collected.
