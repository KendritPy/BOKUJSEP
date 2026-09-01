# Fresh-context handoff

Read this file first. It is the canonical state of the Japanese/Spanish runtime
toggle project as of **2026-09-01**. The detailed evidence lives in the linked
documents; do not reconstruct the project from chat history.

## Goal and non-negotiable constraints

Build a PPSSPP-compatible userspace PRX for **Boku no Natsuyasumi Portable**
(`UCJS10038`) that switches dialogue between the original Japanese and the
TraduSquare/GriffithVIII Spanish v1.0 translation at runtime.

- Use the Spanish v1.0 executable as the runtime base so its horizontal text,
  VWF, expanded layouts, graphics, and new subtitle paths remain available.
- Never modify an input ISO in place or commit copyrighted game data.
- Do not install an address-based hook without an edition-specific byte
  signature and runtime evidence. Fail closed on a mismatch.
- Prefer a structural dialogue identity and whole raw 16-bit streams. A glyph
  hook is a last resort.
- The current PRX is intentionally only a loader and Note-button edge detector.

## Audited public snapshots

Fresh setup is reproducible because `scripts/bootstrap.ps1` pins these refs.
Existing external checkouts are preserved and produce a warning if they differ.

| Source | Audited ref | What it establishes |
|---|---|---|
| [Spanish release](https://github.com/GriffithVIII/Boku-no-Natsuyasumi-ESP) | tag `v1.0` -> `c0e3d2d5417013e4f4b34e416b58743f7efd86ad` | Release claims, credits, screenshots, and patch archive; no source/tooling |
| [Korean project](https://github.com/snake7594/boku-natsu-portable-kr-patch) | tag `v0.1.3-image-kr` / `97d0b30391ccfd44764863b1873f7d0a68246c96` | Current extract/rebuild/font/image tooling and empirical stability reports |
| [Pleonex + GriffithVIII](https://github.com/pleonex/Boku-no-Natsuyasumi) | `dae1215b13ca7dbc6fa17971ecd3d58de86b097a` | 2021 Yarhl/PO rewrite plus GriffithVIII's extended table and second font sheet |
| [PPSSPP](https://github.com/hrydgard/ppsspp/tree/v1.20.4) | tag `v1.20.4` -> `fa50bb1976065c4f8b1b47af227d367fe9771555` | Exact source for the binary and WebSocket behavior under test |

Important lineage detail: Pleonex's default `master` stops at
`c88677d5709338fe1adf0fe61bb9dd43404e55ac` (2015). The public
`feature/yarhl` branch ends at `1b4166bf628d36af36def2fa85552402c6ebe09a`.
GriffithVIII then added the tested extended table (`dbf1d2f...`) and second
font sheet (`dae1215...`). Those two commits are public and fetchable by SHA,
but no current branch names them. Cloning the default branch alone misses all
three improvements.

## What is implemented and verified

- `tools/ppsspp_debug.py` is the only WebSocket transport. It preserves
  interleaved broadcasts/tickets, restores timeouts, uses raw
  `memory.read(replacements=false)`, and falls back to local chunked search on
  1.20.4.
- `tools/dialogue_watch_event_probe.py` recognizes the exact 1.20.4 memcheck
  notification: `cpu.stepping`, `reason=memory.breakpoint`, and
  `relatedAddress=<watch start>`. It also accepts the newer enriched form.
- Watchpoints use `write=true, change=true`, verify the installed entry via
  `memory.breakpoint.list`, and capture evidence before resuming.
- Debug launch uses PPSSPP 1.20.4's supported interpreter flag, `-i`.
- The host F7 bridge presses the otherwise-unused PSP Note button; the PRX
  edge-detects it and toggles its internal state exactly once.
- Unit tests cover transport interleaving, queue preservation, timeout
  restoration, raw reads, and both stepping-event payloads.

Verification command:

```bash
python -m unittest discover -s tests -v
python -m py_compile tools/ppsspp_debug.py tools/dialogue_watch_event_probe.py
git diff --check
```

## Runtime evidence and current boundary

The earlier `0x0881Cxxx` candidates were PPSSPP replacement/emuhack views, not
self-modifying game code. A corrected 32 MiB stable differential using
`replacements=false` left 12 clean line-specific bytes and no changed RAM
pointers.

The strongest surviving line-dependent value is the halfword at `0x0892EBA4`:
it was stable within repeated samples of each textbox and changed from `0x0063`
to `0x01C0` between two textboxes. Its surrounding repeated small halfwords
look like renderer/layout output, not a durable dialogue ID. `0x0892EC00` is a
rejected dialogue-identity candidate because its writer is time-driven state.

No parser, current-line object, font pointer, or safe hook address is accepted
yet. See [findings.md](findings.md) and [addresses.md](addresses.md).

## Exact next experiment

The easiest high-value first pass is now LunaTranslator/LunaHook. It can search
PPSSPP guest hooks directly and may expose the parser call faster than a manual
write-watch trace:

1. Attach current LunaTranslator to PPSSPP 1.20.4 at the early-dialogue save.
2. Search while advancing exactly one textbox and record any stable guest hook
   code, PC/address, register/offset, encoding, and two raw line samples.
3. Cross-check that address with this repository's WebSocket debugger before
   accepting it. Luna is a discovery tool, not a proven in-game write-back
   solution.

See [runtime-tool-survey.md](runtime-tool-survey.md) for the ranked tools,
licenses, forum evidence, and exact adoption boundary. No public `UCJS10038`
hook or script was found.

If Luna yields only OCR/glyph output or no useful hook, continue the existing
authoritative trace, which requires the user's Windows PPSSPP session and
early-dialogue save:

1. Run `launch-debug.bat`; confirm the interpreter build starts.
2. Put a fully rendered textbox on screen.
3. Run `probe-watch-glyph.bat` and follow its prompt.
4. Advance exactly one textbox.
5. Preserve the generated JSON report. A valid 1.20.4 stop has
   `reason=memory.breakpoint` and `relatedAddress=0x0892EBA4`.
6. Use the captured writer PC, GPRs, backtrace, and disassembly to trace
   backward to the parser/lookup boundary. Do not treat `0x0892EBA4` itself as
   the final hook.

If the watch does not fire, inspect `memory.breakpoint.list.hits`, the returned
PPSSPP version, and whether `-i` actually selected the interpreter before
inventing another address.

## Static data strategy after the parser is found

The safe target identity is:

```text
(script file, named-pack member, dialog id/block, text element, segment/run)
```

The game path is `map/gz/*.bin` -> named pack -> gzip member -> unnamed pack ->
member 1 -> dialogue blocks. Text is a little-endian 16-bit word stream. Preserve
control words and original structural boundaries byte-for-byte. See
[boku-dialogue-format.md](boku-dialogue-format.md).

The Korean project demonstrates why fixed slots matter: a naive rebuild
relocated 12 inner members and caused crashes/corruption. Its stable build kept
59 changed script files and 392 audited members at identical inner offsets and
sizes. Translation blobs for this project should therefore be generated from
the JP and ES extracts without repacking either runtime archive.

## What public research did and did not reveal

The Spanish repository and all 16 commits contain only README/LICENSE/image
assets. The v1.0 RAR contains `Leeme.txt`, `Parcheador.exe`, and one xdelta; it
does not publish the translation database, build scripts, assembly patches, or
an EBOOT symbol/address map. The public evidence does show a Pleonex-derived
tool lineage and GriffithVIII's separate PSP ELF expansion utility, but it does
not prove which private tool or revision produced v1.0. See
[spanish-patch-archaeology.md](spanish-patch-archaeology.md).

The Spanish character table and exact JP->ES EBOOT diff remain unknown until a
lawful clean ISO and patched ISO are present. Do not infer either from the
screenshots or the old Pleonex table.

## Documents by purpose

- [architecture.md](architecture.md): intended runtime design and safety model.
- [findings.md](findings.md): chronological measured results and rejected leads.
- [ppsspp-1.20.4-debugger.md](ppsspp-1.20.4-debugger.md): exact debugger protocol
  and memcheck semantics.
- [boku-dialogue-format.md](boku-dialogue-format.md): static archive, script,
  control-word, font, and rebuild facts.
- [spanish-patch-archaeology.md](spanish-patch-archaeology.md): public lineage,
  artifacts, claims, limitations, and excluded lookalike projects.
- [runtime-tool-survey.md](runtime-tool-survey.md): ranked dynamic-hook tools,
  licensing boundaries, forum evidence, and the Luna-first experiment.
- [test-matrix.md](test-matrix.md): end-to-end acceptance coverage.

## Do not repeat these mistakes

- Do not use post-1.20.4 PPSSPP source to describe the 1.20.4 binary.
- Do not wait for a nonexistent `cpu.breakpoint.hit` event.
- Do not send `client.config.set`; the event is `broadcast.config.set`.
- Do not use `change=true` without `write=true`.
- Do not read executable evidence with `replacements=true`.
- Do not launch 1.20.4 with `--cpu=interpreter`; use `-i`.
- Do not clone Pleonex's default branch and assume it is the latest tooling.
- Do not stop blindly at every `0x0000`; it can be a segment/page guard.
- Do not relocate inner dialogue-pack members to make longer text fit.
- Do not claim the public Spanish repository contains its build source.
- Do not copy the public 0xDC00 Agent host: its audited repository has no
  license. Its separate PSP scripts repository is MIT.
- Do not treat Luna extraction/overlay as proof of PSP in-game write-back.
