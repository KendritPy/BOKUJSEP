# Boku Portable dialogue and font format

This is the static-format contract for generating a bilingual mapping. It is
based on Pleonex's format research and 2021 Yarhl parser, then corrected and
extended with the public Korean v0.1.3 toolchain and its checked-in audits.

## Evidence levels

| Level | Meaning | Examples |
|---|---|---|
| Source-confirmed | Two independent public parsers agree | CDIMG sector math, pack entry sizes, block FAT, little-endian words |
| Empirically confirmed | A public patch report records an in-game failure/fix | fixed inner slots; pause trailing-zero guard |
| Working interpretation | Fits code/data but still needs this project's JP/ES runtime check | semantic names for some block/header elements |

## Container path

Dialogue extraction follows this path:

```text
PSP_GAME/USRDIR/
  cdimg.idx + cdimg0.img
    -> map/gz/*.bin                 named pack
      -> M_*.bin.gz (or .gzx)      gzip member
        -> inner unnamed pack
          -> member index 1        dialogue file
            -> block FAT
              -> text element/run  16-bit LE words
```

Do not key bilingual data by a RAM address. A stable static identity is:

```text
(script filename, named-pack index/name, dialog id, block index,
 text element index, segment/run index)
```

Keep both the name and numeric indices. The name helps humans; indices and raw
bytes make the mapping auditable when duplicate IDs exist.

## CDIMG index

`cdimg.idx` starts with `DFI\0`. FAT records are 0x10 bytes:

| Offset | Type | Meaning |
|---:|---|---|
| `+0x00` | `u16` | 0=file, 1=folder |
| `+0x02` | `u16` | file sibling flag or folder child-count encoding |
| `+0x04` | `u32` | name offset relative to this FAT record |
| `+0x08` | `u32` | file sector; byte offset is value * `0x800` |
| `+0x0C` | `u32` | byte size |

Folders are represented recursively in the flat record stream. `cdimg0.img`
members are sector-aligned to `0x800`, not `0x8000`. The latter appears once in
the old wiki prose but contradicts its own formula and both public parsers.

## Compression and packs

- `.gz` is an ordinary gzip stream.
- `.gzx` is `u32 decompressed_size` followed by an ordinary gzip stream.
- Named packs begin with `u32 count`, followed by 0x0C-byte entries
  `(u32 offset, u32 size, u32 name_offset)`.
- Unnamed packs use 0x08-byte entries `(u32 offset, u32 size)`.
- Offsets are absolute from the start of that pack.

Zero offset/size entries may exist and must retain their table position. The
Korean fixed-slot path parses all entries, replaces payloads in place, and pads
shorter compressed results with zero bytes.

## Dialogue file and block layout

The dialogue file begins with `u32 block_count`, then `block_count` FAT entries:

| Offset | Type | Meaning |
|---:|---|---|
| `+0x00` | `u16` | dialog/block ID |
| `+0x02` | `u16` | block byte length |
| `+0x04` | `u32` | block offset from the dialogue-file start |

A block begins with `u32 element_count` followed by that many `u32` offsets,
each relative to the block start. Public parsers treat entries 0-2 as
non-dialogue header data. From entry 3 onward, odd entries are null-terminated
ASCII keys/names and the following even entries are their 16-bit text streams:

```text
3 key, 4 text, 5 key, 6 text, ...
```

The Korean v0.1.3 dataset contains 8,526 unique text identities across 59
top-level `map/gz` scripts and 392 named gzip members. Those counts describe
that public extraction and are a useful completeness check, not a promise that
the Spanish patch retains identical members or boundaries.

## Text words and controls

Words are little-endian `u16` values. Known controls are:

| Word | Meaning | Preservation rule |
|---:|---|---|
| `0x8000` | normal text terminator | preserve the source terminator |
| `0xFFFF` | alternate terminator | preserve; do not normalize to `0x8000` |
| `0x8001` | newline | preserve position unless reflow is intentional and tested |
| `0x8002` | page/pause control | consumes the following argument word |
| `0x0000` | segment break, page guard, or context-dependent end | never discard by a blind C-string rule |

The tested multi-page form is:

```text
0x8002, argument, 0x0000, first word of next page, ...
```

The Korean v0.1.1 experiment removed that zero and observed missing first
characters on later pages. v0.1.2 restored `8002 hhhh 0000`. This corrects the
legacy Pleonex parser, which stopped at every `0x0000` and therefore could lose
later runs.

Zero still appears as a genuine run/segment boundary, and older extracted rows
may label it a terminator. Interpret it using the element's outer offset/length,
the preceding `0x8002`, and neighboring runs. Preserve raw source words even
when the semantic label is uncertain.

## Character tables and font atlases

Character codes index 16x16 glyph tiles. The public Korean implementation uses:

```text
atlas_index = code // 1024
tile_index  = code % 1024
tile_x      = (tile_index % 32) * 16
tile_y      = (tile_index // 32) * 16
```

The two 512x512, 4-bpp swizzled PIM2 sheets are inside the unnamed `font.bin`
pack, itself inside the named `startup.bin.gzx` pack. PIM2 pixel data is PSP
swizzled; editing a linear PNG without re-swizzling will corrupt the atlas.

Pleonex's embedded parser reads the older decimal table syntax such as
`0000 = 　`; it parses the first four characters as **decimal**, not hex. Its
separate `Boku_noENDIAN.tbl` uses byte-order-oriented hex keys for external
table tools and must not be fed to the decimal parser. Mixing these two table
formats silently maps the wrong glyphs.

The Korean v0.1.3 font table has codes 0-2019. Its glyph map adds 996 glyphs in
the second sheet, codes 1024-2019. These numbers describe the Korean patch,
not the Spanish mapping. The Spanish code table must be derived from the
Spanish ISO/font assets or runtime lookup, not assumed from either public table.

## Safe rebuild rules

1. Preserve the exact original raw stream and terminator beside every decoded
   string.
2. Rebuild from highest offset to lowest when lengths can change, or rebuild
   the block's offset table explicitly.
3. Prefer fixed block/member slots. Reject a text stream that cannot fit rather
   than silently moving following data.
4. Require each recompressed inner member to fit its original named-pack slot;
   zero-pad the remainder and retain the original entry offset and size.
5. If every replaced CDIMG member keeps its byte length, patch `cdimg0.img` in
   place and leave `cdimg.idx` unchanged.
6. Treat full-CDIMG repacking and inner-dialogue relocation as separate,
   opt-in operations with explicit audits.
7. Compare all pack offsets/sizes before and after, then run autoplay/idle,
   background, multi-page, save/load, and scene-transition tests.

The Korean reports document why these guards exist: 12 silently relocated
members caused crashes or asset corruption; the stable repair compacted spaces
in 46 rows, changed no inner offsets/sizes, and trimmed no content. The later
pause-guard build used 80 space-compaction actions and still trimmed no content.

## Implications for the runtime toggle

The PRX should not repack CDIMG at runtime. Build an immutable bilingual blob
offline from paired JP/ES structural identities and exact raw word streams.
At the narrowest verified parser/lookup boundary, select the JP or ES stream
for the current identity and let the Spanish renderer process it.

Before committing to that design, measure whether the Spanish EBOOT's font
lookup can render the original Japanese codes and whether its parser preserves
the same block/element identity. If it cannot, the blob needs an edition-aware
code mapping or separate font/table state; that is still an open experiment.

