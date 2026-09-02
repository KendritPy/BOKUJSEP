# Boku Portable dialogue format

This document records the serialized structures BokuLangToggle depends on. The implementation preserves raw game words and structural identities; decoded strings are for inspection only.

## Container path

```text
PSP_GAME/USRDIR/
  cdimg.idx + cdimg0.img
    -> map/gz/*.bin
      -> M_*.bin.gz / .gzx
        -> unnamed pack
          -> member 1
            -> dialogue file
              -> block
                -> text element/run
```

A stable dialogue identity is based on this structure, not on a runtime RAM address:

```text
(script, named-pack member, dialog/block id, text element, segment/run)
```

## CDIMG and packs

`cdimg.idx` begins with `DFI\0`. File offsets are stored in `0x800`-byte sectors. Named packs contain a count followed by `0x0C`-byte entries `(offset, size, name_offset)`; unnamed packs use `0x08`-byte `(offset, size)` entries. `.gz` members are ordinary gzip streams; `.gzx` adds a 32-bit decompressed-size prefix before the gzip data.

Zero-sized entries and original table positions must be preserved when rebuilding.

## Dialogue blocks

A dialogue file begins with a 32-bit block count followed by entries containing a 16-bit ID, 16-bit block length, and 32-bit block offset.

Each block starts with an element count and an offset table. In the public parsers used as the basis for this project, entries from index 3 onward alternate between ASCII key/name data and 16-bit text streams:

```text
3 key, 4 text, 5 key, 6 text, ...
```

The bilingual builder keeps the exact raw stream beside every decoded representation so control words and terminators are never reconstructed from text.

## Text words

Words are little-endian `u16` values. Controls required by the current pipeline include:

| Word | Meaning / rule |
| ---: | --- |
| `0x8000` | normal text terminator; preserve exactly |
| `0xFFFF` | alternate terminator; preserve exactly |
| `0x8001` | newline |
| `0x8002` | page/pause control; consumes the following argument |
| `0x0000` | segment/page guard or context-dependent boundary; never discard blindly |

The verified multi-page sequence is:

```text
0x8002, argument, 0x0000, first word of next page, ...
```

Removing that zero can drop the first visible character of the following page. Page boundaries are therefore parsed from the enclosing element and control sequence rather than by treating every zero as a C-string terminator.

## Font atlases

Character codes index 16x16 glyph tiles across 512x512 4-bpp PIM2 sheets:

```text
atlas_index = code // 1024
tile_index  = code % 1024
tile_x      = (tile_index % 32) * 16
tile_y      = (tile_index // 32) * 16
```

The PIM2 pixel data is PSP-swizzled. The JP and ES atlases are extracted from their respective game images during the local build; the runtime plugin swaps the appropriate atlas instead of assuming one edition's code table applies to the other.

## Runtime mapping rules

The offline builder pairs JP and ES records by structural identity and stores their exact raw streams in an immutable blob. It also records context needed to reject ambiguous ES signatures and page-count mismatches.

At runtime the verified dialogue hook resolves the current ES record. Japanese mode substitutes the corresponding JP page ordinal, restores the JP atlas, and uses the original fixed 16-pixel advance. If the record is unresolved, ambiguous, or page-incompatible, the plugin stays in or falls back to Spanish.

These rules deliberately prefer a missed toggle over corrupt text, wrong-record substitution, or mixed renderer state.
