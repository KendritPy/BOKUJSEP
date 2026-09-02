#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import struct
import sys
from pathlib import Path

from ppsspp_debug import PPSSPPDebugger
from compare_eboot import parse_elf, RUNTIME_LOAD_BIAS

ROOT = Path(__file__).resolve().parents[1]
ES_RECORD_INDEX = 4978
SCRIPT = "G2a.bin"
KEY = "0122_12"
SEARCH_BASE = 0x0D000000
SEARCH_SIZE = 0x00D00000  # 0x0DD00000 begins an invalid PPSSPP memory gap.
CHUNK_SIZE = 0x00100000
WRITE_CHUNK_SIZE = 0x00004000
TEXT_WALKER_START = 0x0881BE1C
TEXT_WALKER_END = 0x0881C304
# Spanish loads a signed proportional width from its injected Latin table.
# Japanese atlas cells are the original 16x16 monospaced glyphs.  In mixed
# mode, retain the Spanish helper and accumulator but replace only that load
# with `li s6,0x10`; the following store writes the correct fixed advance.
SPANISH_WIDTH_LOAD_ADDRESS = 0x0891B5D4
SPANISH_WIDTH_LOAD_WORD = 0x80B60000  # lb s6,0(a1)
JAPANESE_FIXED_WIDTH_WORD = 0x24160010  # li s6,0x10


def locate_unique(haystack: bytes, needle: bytes, base: int) -> int:
    first = haystack.find(needle)
    if first < 0:
        raise RuntimeError("the exact visible Spanish stream is not resident")
    if haystack.find(needle, first + 1) >= 0:
        raise RuntimeError("the exact Spanish stream is not unique in live memory")
    return base + first


def load_pair() -> tuple[bytes, bytes, dict[str, object]]:
    es_records = json.loads((ROOT / "data/es/dialogue.json").read_text(encoding="utf-8"))
    pairs = json.loads((ROOT / "data/bilingual/dialogue_pairs.json").read_text(encoding="utf-8"))
    es_record = es_records[ES_RECORD_INDEX]
    if es_record.get("script") != SCRIPT or es_record.get("key") != KEY:
        raise RuntimeError("canonical ES record identity changed; refusing live write")
    es_raw = bytes.fromhex(es_record["raw_hex"])
    pair = next(
        (
            item for item in pairs
            if item.get("script") == SCRIPT
            and item.get("key") == KEY
            and item.get("es", {}).get("raw") == es_record["raw_hex"]
        ),
        None,
    )
    if pair is None:
        raise RuntimeError("paired Japanese record was not found")
    jp_raw = bytes.fromhex(pair["jp"]["raw"])
    if len(jp_raw) > len(es_raw):
        raise RuntimeError("Japanese proof stream does not fit the Spanish buffer")
    return es_raw, jp_raw, pair


def load_atlas(edition: str, atlas_index: int = 0) -> bytes:
    source = ROOT / "external/boku-korean-tools/tools/boku_tools.py"
    spec = importlib.util.spec_from_file_location(f"boku_tools_swap_{edition}", source)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    startup = ROOT / f"extracted/{edition}/cdimg/01startup/startup.bin.gzx"
    payload = gzip.decompress(startup.read_bytes()[4:])
    startup_entries = module.parse_pack_entries(payload, with_names=True)
    font_entry = next(item for item in startup_entries if item["name"].lower() == "font.bin")
    font_pack = payload[font_entry["offset"]:font_entry["offset"] + font_entry["size"]]
    images = []
    for entry in module.parse_pack_entries(font_pack, with_names=False):
        image = font_pack[entry["offset"]:entry["offset"] + entry["size"]]
        if image.startswith(b"PIM2"):
            images.append(image)
    return images[atlas_index]


def write_chunks(session: PPSSPPDebugger, address: int, data: bytes) -> None:
    for offset in range(0, len(data), WRITE_CHUNK_SIZE):
        session.write(address + offset, data[offset:offset + WRITE_CHUNK_SIZE])


def load_code_patches(*, width_only: bool = True) -> list[tuple[int, bytes, bytes]]:
    paths = {
        "jp": ROOT / "extracted/jp/iso/PSP_GAME/SYSDIR/BOOT.BIN",
        "es": ROOT / "extracted/es/iso/PSP_GAME/SYSDIR/EBOOT.BIN",
    }
    ranges: dict[str, bytes] = {}
    for edition, path in paths.items():
        _, sections = parse_elf(path)
        text = sections[".text"]
        offset = TEXT_WALKER_START - (RUNTIME_LOAD_BIAS + text.address)
        ranges[edition] = text.data[offset:offset + TEXT_WALKER_END - TEXT_WALKER_START]
    differences = []
    for offset in range(0, len(ranges["jp"]), 4):
        jp_word = ranges["jp"][offset:offset + 4]
        es_word = ranges["es"][offset:offset + 4]
        address = TEXT_WALKER_START + offset
        if jp_word != es_word:
            differences.append((address, es_word, jp_word))
    if not width_only:
        return differences
    return [(
        SPANISH_WIDTH_LOAD_ADDRESS,
        struct.pack("<I", SPANISH_WIDTH_LOAD_WORD),
        struct.pack("<I", JAPANESE_FIXED_WIDTH_WORD),
    )]


def apply_code(session: PPSSPPDebugger, patches: list[tuple[int, bytes, bytes]], japanese: bool) -> None:
    expected_index, replacement_index = (1, 2) if japanese else (2, 1)
    for patch in patches:
        address = patch[0]
        expected = patch[expected_index]
        replacement = patch[replacement_index]
        actual = session.read(address, 4)
        if actual != expected:
            raise RuntimeError(
                f"text-walker signature mismatch at 0x{address:08X}: "
                f"expected {expected.hex().upper()}, got {actual.hex().upper()}"
            )
        session.write(address, replacement)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reversibly swap the known visible dinner line to Japanese")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "analysis/debugger/known-line-swap.json",
    )
    args = parser.parse_args()

    es_raw, jp_raw, pair = load_pair()
    es_atlas = load_atlas("es")
    jp_atlas = load_atlas("jp")
    if len(es_atlas) != len(jp_atlas):
        raise RuntimeError("JP/ES atlas-0 sizes differ")
    code_patches = load_code_patches(width_only=True)
    all_code_differences = load_code_patches(width_only=False)
    session = PPSSPPDebugger(args.host, args.port, timeout=10.0)
    address: int | None = None
    atlas_address: int | None = None
    changed = False
    report: dict[str, object] = {
        "identity": {
            "id": pair["id"], "script": SCRIPT, "key": KEY,
            "dialog_id": pair["dialog_id"], "block_index": pair["block_index"],
            "element_index": pair["element_index"],
        },
        "es_size": len(es_raw),
        "jp_size": len(jp_raw),
        "atlas_size": len(es_atlas),
        "atlas_changed_bytes": sum(left != right for left, right in zip(es_atlas, jp_atlas)),
        "text_walker_patches": [
            {
                "address": f"0x{address:08X}",
                "es_word": f"0x{struct.unpack('<I', es_word)[0]:08X}",
                "jp_word": f"0x{struct.unpack('<I', jp_word)[0]:08X}",
            }
            for address, es_word, jp_word in code_patches
        ],
        "text_walker_differences_not_applied": [
            f"0x{address:08X}"
            for address, _es_word, _jp_word in all_code_differences
        ],
    }
    try:
        report["game_status"] = session.request("game.status")
        memory = bytearray()
        for offset in range(0, SEARCH_SIZE, CHUNK_SIZE):
            size = min(CHUNK_SIZE, SEARCH_SIZE - offset)
            memory.extend(session.read(SEARCH_BASE + offset, size))
        address = locate_unique(memory, es_raw, SEARCH_BASE)
        atlas_address = locate_unique(memory, es_atlas, SEARCH_BASE)
        report["address"] = f"0x{address:08X}"
        report["atlas_address"] = f"0x{atlas_address:08X}"
        if session.read(address, len(es_raw)) != es_raw:
            raise RuntimeError("live signature changed before write")
        if session.read(atlas_address, len(es_atlas)) != es_atlas:
            raise RuntimeError("live Spanish atlas signature changed before write")

        for code_address, es_word, _jp_word in code_patches:
            if session.read(code_address, 4) != es_word:
                raise RuntimeError(f"live Spanish text-walker signature mismatch at 0x{code_address:08X}")

        input("Exact Spanish line, atlas, and layout code found. Press ENTER for complete Japanese mode: ")
        replacement = jp_raw + bytes(len(es_raw) - len(jp_raw))
        changed = True
        apply_code(session, code_patches, japanese=True)
        write_chunks(session, atlas_address, jp_atlas)
        session.write(address, replacement)
        if session.read(address, len(es_raw)) != replacement:
            raise RuntimeError("Japanese proof write did not verify")
        if session.read(atlas_address, len(jp_atlas)) != jp_atlas:
            raise RuntimeError("Japanese atlas proof write did not verify")
        print("Japanese stream, atlas, and original layout logic active. Look at PPSSPP without advancing.")
        input("Press ENTER here to restore complete Spanish mode and exit: ")
        session.write(address, es_raw)
        write_chunks(session, atlas_address, es_atlas)
        apply_code(session, code_patches, japanese=False)
        changed = False
        if session.read(address, len(es_raw)) != es_raw:
            raise RuntimeError("Spanish restore did not verify")
        if session.read(atlas_address, len(es_atlas)) != es_atlas:
            raise RuntimeError("Spanish atlas restore did not verify")
        report["result"] = "swapped_and_restored"
        print("Spanish stream restored and verified.")
    except Exception as exc:
        report.setdefault("result", "error")
        report["error"] = str(exc)
        raise
    finally:
        if changed and address is not None:
            try:
                session.write(address, es_raw)
                if atlas_address is not None:
                    write_chunks(session, atlas_address, es_atlas)
                # Restore only words currently carrying their JP form. This
                # handles partial application without masking the first error.
                for code_address, es_word, jp_word in code_patches:
                    if session.read(code_address, 4) == jp_word:
                        session.write(code_address, es_word)
                report["emergency_restore"] = "written"
            except Exception as exc:
                report["emergency_restore"] = f"failed: {exc}"
        session.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
