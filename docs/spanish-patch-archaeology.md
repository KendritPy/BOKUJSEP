# Spanish patch and public-tool archaeology

This audit records what is publicly reproducible about the Spanish translation
and the tools associated with its credited romhacker and predecessors. It
separates confirmed facts from plausible lineage so a new agent does not turn a
GitHub association into an unsupported technical claim.

Audit date: **2026-09-01**.

## Confirmed Spanish release facts

The official [TraduSquare project page](https://tradusquare.es/proyectos/boku-no-natsuyasumi/),
[2021 announcement](https://tradusquare.es/anunciamos-la-traduccion-de-boku-no-natsuyasumi-portable/),
[2025 release post](https://tradusquare.es/boku-no-natsuyasumi-ya-disponible-en-espanol/),
and [GitHub repository](https://github.com/GriffithVIII/Boku-no-Natsuyasumi-ESP)
agree on the following public scope:

- the project ran for nearly four years and released v1.0 on 2025-08-01;
- game dialogue, graphics, insect names, cinematics, minigames, and save-data
  presentation are described as fully translated;
- menus were widened and a variable-width font was added;
- EBOOT code changes add horizontal dialogue and subtitles for television,
  insect sumo, insect catches, endings, and other scenes, plus an altered
  insect-collection board;
- GriffithVIII is credited for romhacking and project leadership; Atalavan,
  Stogran, and 堕落王 are credited for translation; Pleonex, Snake128, obskyr,
  Hilltop, Ortew, and Infrid appear in acknowledgements.

These are release claims, not a source-level description of how each feature
was implemented.

## What the public release actually contains

The repository's only branch is `main`; its 16-commit history runs from
2025-07-26 through 2026-08-04. Across every commit, the only paths are:

- `README.md` and `LICENSE`;
- `assets/banner.png` and numbered screenshots.

Some screenshots were added, replaced, or deleted. No source, assembly,
translation database, table, build script, patch definition, or EBOOT map ever
appears in that Git history.

The v1.0 tag is the lightweight tag
`c0e3d2d5417013e4f4b34e416b58743f7efd86ad`. The current documentation commit
is `86820b58d881c9d947b87f6a913297bc9aec8163`; it postdates the release and does
not change the patch.

The official `bokuES-v1.0.rar` has SHA-256
`F38EDCE9CFEAD315574460F9F0356AFF1B6EE03FD22AD023D09CA11B24F735F7`
and contains only:

| Path | Uncompressed size |
|---|---:|
| `bokuES-v1.0/Leeme.txt` | 2,124 bytes |
| `bokuES-v1.0/Parcheador.exe` | 3,964,928 bytes |
| `bokuES-v1.0/patch/bokuES-v1.0.xdelta` | 136,798,233 bytes |

The xdelta SHA-256 is
`B6F4145FD880406CC56D9F3C929A56E642F0218EEBC03E9ECE84C3C9228074C3`.
The archive publishes a binary patch and generic patching front end, not a
rebuildable source tree.

## Public tool lineage

### Pleonex's original work

[pleonex/Boku-no-Natsuyasumi](https://github.com/pleonex/Boku-no-Natsuyasumi)
is the earliest public PSP-format foundation found. Its default `master` ends
at `c88677d5709338fe1adf0fe61bb9dd43404e55ac` (2015-08-15) and contains the
older C# Bokuract extractor, format validators, script/XML support, a table,
font image, and MIPS research notes.

The associated [wiki](https://github.com/pleonex/Boku-no-Natsuyasumi/wiki)
documents `cdimg.idx`/`cdimg0.img`, named and unnamed packs, `.gz`/`.gzx`, the
dialogue block layout, controls, and two font sheets. One wiki sentence says
CDIMG members are padded to `0x8000`; its FAT formula says offsets are measured
in `0x800` sectors, and both the Pleonex parser and Korean rebuild code use
`0x800`. Treat `0x8000` there as a documentation typo.

### The branch that default clones miss

The public `feature/yarhl` branch ends at
`1b4166bf628d36af36def2fa85552402c6ebe09a` (2021-04-01). It migrates Bokuract
to Yarhl 3 and exports all `map/gz` dialogue to PO. The PO context is
`script-member:dialog-id:text-index`.

The branch is useful for parsing and provenance but is not a complete
translation build system:

- it exports PO but does not import PO and rebuild the game;
- its parser stops at `0x0000`, losing later runs when zero is an embedded
  segment/page guard;
- its embedded `Table` allocates 1,024 characters and does not consume the
  later extended two-sheet table;
- it has none of the Korean project's fixed-slot/relocation audits.

### GriffithVIII's public Boku commits

Two direct descendants of `feature/yarhl` remain fetchable from the Pleonex
repository even though no branch points to them:

| Commit | Date | Change |
|---|---|---|
| [`dbf1d2f31121e414eb32802c493c984be2f3a929`](https://github.com/pleonex/Boku-no-Natsuyasumi/commit/dbf1d2f31121e414eb32802c493c984be2f3a929) | 2021-04-08 | GriffithVIII: extended table with kanji, noted as tested in game |
| [`dae1215b13ca7dbc6fa17971ecd3d58de86b097a`](https://github.com/pleonex/Boku-no-Natsuyasumi/commit/dae1215b13ca7dbc6fa17971ecd3d58de86b097a) | 2021-04-08 | GriffithVIII: second font sheet |

The wiki's `font2.png` link names a former
`GriffithVIII/Boku-no-Natsuyasumi` fork that is no longer public. The identical
commit objects are nevertheless public from Pleonex and several forks. The
second font image is therefore recoverable; the Spanish project's later
private modifications are not.

### Other public GriffithVIII tools

[PSP_ELFHandler](https://github.com/GriffithVIII/PSP_ELFHandler) is a C#/Yarhl
command-line utility that inserts an additional loadable RWX segment into a PSP
ELF/EBOOT and shifts program/section offsets. Its purpose is compatible with
the release's substantial EBOOT additions, but no public commit, release note,
or build script proves that it produced the Spanish EBOOT. Also note that its
README invocation omits the `INCREASE` verb required by `Program.cs`; audit the
code before attempting to reuse it.

[TIMVisor](https://github.com/GriffithVIII/TIMVisor) edits PlayStation 1 TIM
graphics. Boku Portable's relevant font atlases are PSP PIM2 data inside
`startup.bin`, so TIMVisor is not evidence for the PSP font pipeline.
GriffithVIII's other currently public repositories did not expose a Boku
translation database or patch builder.

## The most complete public successor

[snake7594/boku-natsu-portable-kr-patch](https://github.com/snake7594/boku-natsu-portable-kr-patch)
at `v0.1.3-image-kr` is the most complete reproducible first-game PSP pipeline
found. It includes Python extraction/rebuild code, the table and glyph map,
8,526 structured translation rows, image patching, release xdelta, and static
audit reports.

The reports contain two critical empirical corrections absent from Pleonex:

1. A naive repack relocated 12 `map/gz` members and was associated with idle or
   autoplay crashes and house-background corruption. The repaired build keeps
   59 changed script files and 392 audited members at unchanged inner offsets
   and sizes.
2. A page control must remain `8002 hhhh 0000`; removing the trailing zero can
   make the first visible character on the next page disappear.

This code is strong implementation evidence, but it is a Korean successor
project, not the unpublished Spanish source. Use it to understand formats and
failure modes, not to assert Spanish byte-for-byte behavior.

## Public projects checked and excluded

- `sunkper/Project-Summer-Island` is a Godot recreation of a Boku 2 scene, not
  a translation or reverse-engineering tool.
- `psyouloveme/boku1-reversing` targets the original PlayStation game with
  BizHawk/Ghidra material, not the PSP port's CDIMG/dialogue pipeline.
- Hilltop's Boku 2 translation repositories concern the PS2 sequel and cannot
  supply PSP addresses or container invariants.
- Surviving Pleonex forks preserve commits and minor framework updates but do
  not expose the missing Spanish build tree.

## What remains unknown

Until both lawful JP and Spanish-patched ISOs are available, the following must
remain explicitly unknown:

- the Spanish character-code table and the exact handling of accents;
- the JP-to-ES EBOOT code/data diff, injected segment layout, and hook sites;
- the private translation database and how its identities map to the runtime;
- which public or private version of Bokuract/PSP_ELFHandler was used;
- whether Spanish dialogue members were rebuilt in fixed slots or relocated;
- stable runtime parser/text-object/font pointers.

The project pipeline should answer these with hashes, structured file diffs,
font coverage, EBOOT disassembly, and runtime evidence. Public screenshots or
credit lists are not substitutes.

