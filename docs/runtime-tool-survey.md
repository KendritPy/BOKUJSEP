# Runtime translation tool survey

Last audited: **2026-09-01**. This is the adoption decision for the next agent,
not a catalog of every translation utility. The target is still an in-game
Japanese/Spanish toggle for `UCJS10038`; an OCR or machine-translation overlay
is useful only as a discovery aid or fallback.

## Decision

Use **LunaTranslator/LunaHook first to discover and validate the guest text
hook**, then implement the proven hook in the existing **PSPModBase PRX**. Use
**TF-MultiFix** as the closest MIT-licensed implementation reference for the
final PRX. This is the shortest credible path and does not make LunaTranslator
a runtime dependency of the finished patch.

Do not start by forking PPSSPP, reviving Textractor, or building a new Frida
host. Those routes add substantial maintenance before answering the one
unknown that currently matters: which guest instruction receives or decodes a
dialogue stream.

## Ranked options

Scores are project-specific. “Final fit” means suitability for a reliable
in-game JP/ES switch, not general translation quality.

| Rank | Tool | Ease | Maturity | Final fit | License | Decision |
|---:|---|---:|---:|---:|---|---|
| 1 | [LunaTranslator](https://github.com/HIllya51/LunaTranslator) / LunaHook | 5/5 | 5/5 | 2/5 alone | GPL-3.0 | Adopt now for PPSSPP hook search, extraction, and live verification |
| 2 | [PSPModBase](https://github.com/xan1242/PSPModBase) + [TF-MultiFix](https://github.com/xan1242/TF-MultiFix) patterns | 3/5 | 4/5 | 5/5 | MIT | Keep as the shipped solution after the hook is proven |
| 3 | [0xDC00 scripts](https://github.com/0xDC00/scripts) | 3/5 | 3/5 | 2/5 alone | MIT | Useful guest-address/filter examples; do not depend on its unlicensed host |
| 4 | [Textractor](https://github.com/Artikash/Textractor) | 2/5 | 3/5 historical | 1/5 | GPL-3.0 | Legacy fallback only; modern PPSSPP reports favor Luna |
| 5 | PPSSPP WebSocket debugger | 2/5 | 5/5 | 4/5 | GPL-2.0+ | Retain as the authoritative tracer and independent cross-check |
| 6 | OCR/screen translation | 5/5 | 4/5 | 0/5 | varies | Playback fallback only; it cannot supply the intended in-game toggle |

## Why LunaTranslator is the easiest useful next step

The current LunaHook source contains a dedicated PPSSPP engine and JIT-aware
guest-address hooks. Its manual hook form is:

```text
{hook parameters}@{guest address}:JIT:PPSSPP
```

The official emulator documentation supports PPSSPP 1.15.0 and newer, so the
project's pinned PPSSPP 1.20.4 is in scope. The repository was active on the
audit date (about 13,000 stars, more than 1,100 forks, and a same-day release),
which makes it materially safer to try than abandoned hookers.

No `UCJS10038`, Boku no Natsuyasumi, or equivalent script was present in the
audited Luna source. Luna's documented emulator path proves extraction and
translation display; it does **not** prove that PPSSPP text can be written back
into the game. Treat it as a hook finder and observable text feed, not as the
finished toggle.

### Exact Luna experiment

1. Start the pinned PPSSPP 1.20.4 interpreter build and load the Spanish v1.0
   ISO at the early-dialogue save.
2. Attach LunaTranslator using its PPSSPP/emulator mode.
3. Search hooks while advancing exactly one textbox. Reject UI, logging, and
   repeated glyph hooks; prefer one emission per dialogue segment.
4. Record the hook code, guest PC/address, selected register/offset, encoding,
   and raw bytes for two distinct lines.
5. Cross-check that guest address with `tools/ppsspp_debug.py`; if necessary,
   correlate it with the writer captured from `0x0892EBA4`.
6. Decode the same raw bytes with the Boku table and verify structural control
   words. Only then promote the address to a PRX hook candidate.

If Luna produces only glyphs or OCR, it has still falsified the easy parser
path. Resume the existing WebSocket watchpoint trace rather than engineering a
new Luna backend.

## Closest open implementation to copy from

TF-MultiFix is the most relevant public MIT example found. It is a real
PSP/PPSSPP PRX that:

- detects PPSSPP and discovers loaded PSP modules;
- converts absolute reverse-engineering results into module-relative patches;
- hooks dynamically loaded game PRXs through load callbacks;
- uses `minjector` for MIPS `CALL`/`JMP` patches and flushes caches;
- hooks language selection and optionally treats story data as UTF-8;
- supplies an in-game configuration UI.

These patterns map directly to BokuLangToggle. TF-MultiFix mostly relies on
known per-edition offsets, however; it is not evidence that our candidate is
safe. Copy its module/load/cache architecture, but retain this repository's
stricter edition hash, byte-signature, bounds, and fail-closed requirements.

[TFEhpLoader](https://github.com/xan1242/TFEhpLoader) is another small MIT PSP
example that loads replacement resources externally. It becomes relevant only
if the final design needs assets on the memory stick; it does not solve
dialogue interception by itself. The mature MIT
[WidescreenFixesPack](https://github.com/ThirteenAG/WidescreenFixesPack) is good
`minjector` lineage but much less specific than TF-MultiFix.

## Other hookers and repositories

### 0xDC00 Agent

The MIT `0xDC00/scripts` repository contains `libPPSSPP.js` and 22
game-specific PSP scripts. They demonstrate the useful minimal model: a guest
address, register/offset decoder, and text filter. No Boku script was found.

The separate [Agent repository](https://github.com/0xDC00/agent) publishes a
binary-oriented README but, at the audited root, no source and no license.
Public availability is not permission to fork or redistribute it. Its MIT
scripts may be studied or reused under their terms; the host must remain an
optional external experiment unless its licensing changes.

### Textractor and older ITH/VNR paths

A [2020 PPSSPP extraction tutorial](https://aurora6290.wordpress.com/2020/08/28/tutorial-on-extracting-text-from-psp-games/)
shows that this family worked historically, and
[Textractor issue 165](https://github.com/Artikash/Textractor/issues/165)
records PPSSPP hook-finding work. That evidence is valuable but old. A
[2024 PPSSPP failure report](https://github.com/Artikash/Textractor/issues/1358)
redirects users to LunaTranslator, whose author describes Luna as the
maintainable successor in
[Textractor issue 1252](https://github.com/Artikash/Textractor/issues/1252).
Do not spend the next session repairing Textractor unless Luna fails in a way
Textractor demonstrably handles.

### Rejected as primary bases

- A full PPSSPP fork is mature but creates a large GPL emulator-maintenance
  burden and would not run on real PSP hardware.
- `EmuHook` and `ppsspp-gpihook` are small public experiments without a clear
  reusable license in the audited metadata; neither provides a Boku hook.
- OCR and RetroArch-style AI translation translate pixels, not Boku's raw
  dialogue identity. They cannot preserve the supplied human Spanish streams
  or implement an internal JP/ES switch.

## Evidence from users and forums

- A current Boku community post reports playing
  [Boku no Natsuyasumi 3 with LunaTranslator](https://www.reddit.com/r/BokuNoNatsuyasumi/comments/1w3h0sb/boku_no_natsuyasumi_3_playing_with_lunatranslator/).
  This validates usability on a related title, but it uses RPCS3 and is not a
  hook for the PSP game.
- A current PSP-series question is answered with
  [LunaTranslator as a screen-translation option](https://www.reddit.com/r/BokuNoNatsuyasumi/comments/1v6atbk/is_there_any_way_to_play_it_in_english/).
- The public Agent discussion says each game/engine needs a specific script,
  matching the absence of a universal Boku hook.

No public forum post, repository, hook code, address map, or ready-to-fork
solution for `UCJS10038` was found in the final search. “Boku No Translator”
appears as a community post title, but the indexed evidence did not expose a
reusable tool or source, so it must not be cited as one.

## Licensing boundary

Noncommercial use does not override copyright or a missing license.

- MIT code can be incorporated with its copyright/license notice.
- GPL tools can be run separately with no effect on this repository's license.
- Copying GPL implementation code into the distributed PRX would require
  satisfying the GPL for the resulting derivative work.
- Code with no license may be read for facts and ideas but not copied,
  redistributed, or used as a fork base without permission.

Record the exact upstream commit and license of any code actually adopted.

## Stop condition for the next agent

The survey is complete. Do not repeat broad searches before running the Luna
experiment. Search again only after obtaining a concrete hook code, writer PC,
or failure mode that supplies a narrower query. The next durable deliverable is
runtime evidence for one dialogue boundary, not another list of tools.
