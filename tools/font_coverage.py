#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import struct
import sys
from collections import Counter
from pathlib import Path

from common import hash_file, write_json


ROOT = Path(__file__).resolve().parents[1]


def load_table(path: Path) -> dict[int, str]:
    table: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if len(line) >= 8:
            try:
                table[int(line[:4])] = line[7:]
            except ValueError:
                pass
    return table


def used_codes(dialogue_path: Path) -> Counter[int]:
    records = json.loads(dialogue_path.read_text(encoding="utf-8"))
    result: Counter[int] = Counter()
    for record in records:
        raw = bytes.fromhex(record["raw_hex"])
        words = struct.unpack(f"<{len(raw) // 2}H", raw[: len(raw) // 2 * 2])
        result.update(word for word in words if 0x0001 <= word <= 0x0400)
    return result


def pim2_containers(root: Path) -> list[dict[str, object]]:
    found = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name == ".complete":
            continue
        data = path.read_bytes()
        count = data.count(b"PIM2")
        if count:
            found.append({
                "path": path.relative_to(root).as_posix(), "pim2_signatures": count,
                "size": len(data), "sha256": hash_file(path, ("sha256",))["sha256"],
            })
    return found


def load_boku_tools():
    source = ROOT / "external" / "boku-korean-tools" / "tools" / "boku_tools.py"
    spec = importlib.util.spec_from_file_location("boku_tools_font", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def font_glyphs(edition: str) -> tuple[list[dict[str, object]], dict[int, bytes]]:
    boku = load_boku_tools()
    startup = ROOT / "extracted" / edition / "cdimg" / "01startup" / "startup.bin.gzx"
    original = startup.read_bytes()
    payload = gzip.decompress(original[4:])
    startup_entries = boku.parse_pack_entries(payload, with_names=True)
    font_entry = next(entry for entry in startup_entries if entry["name"].lower() == "font.bin")
    font_pack = payload[font_entry["offset"] : font_entry["offset"] + font_entry["size"]]
    entries = boku.parse_pack_entries(font_pack, with_names=False)
    metadata: list[dict[str, object]] = []
    glyphs: dict[int, bytes] = {}
    for atlas_index, entry in enumerate(entries):
        image = font_pack[entry["offset"] : entry["offset"] + entry["size"]]
        if not image.startswith(b"PIM2"):
            continue
        image_offset, data_size, width, height = boku.pim2_4bpp_info(image)
        linear = boku.unswizzle_4bpp(image[image_offset : image_offset + data_size], width, height)
        columns, rows = width // 16, height // 16
        metadata.append({
            "atlas_index": atlas_index, "width": width, "height": height,
            "glyph_slots": columns * rows, "entry_size": entry["size"],
        })
        for local_code in range(columns * rows):
            tile_x, tile_y = (local_code % columns) * 16, (local_code // columns) * 16
            tile = bytearray()
            for y in range(16):
                start = (tile_y + y) * (width // 2) + tile_x // 2
                tile.extend(linear[start : start + 8])
            glyphs[atlas_index * 1024 + local_code] = bytes(tile)
    return metadata, glyphs


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit dialogue code coverage and PIM2-containing resources")
    parser.add_argument("--jp-table", type=Path, default=ROOT / "external" / "boku-pleonex" / "font" / "table.txt")
    parser.add_argument("--es-table", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "analysis" / "fonts" / "coverage.json")
    args = parser.parse_args()
    jp_table = load_table(args.jp_table)
    es_table = load_table(args.es_table) if args.es_table else jp_table
    jp_codes = used_codes(ROOT / "data" / "jp" / "dialogue.json")
    es_codes = used_codes(ROOT / "data" / "es" / "dialogue.json")
    jp_atlases, jp_glyphs = font_glyphs("jp")
    es_atlases, es_glyphs = font_glyphs("es")
    all_codes = sorted(jp_codes.keys() | es_codes.keys())
    comparable = sorted(jp_glyphs.keys() & es_glyphs.keys())
    changed_glyphs = [code for code in comparable if jp_glyphs[code] != es_glyphs[code]]
    report = {
        "table_status": "separate" if args.es_table else "ES decoding provisional with JP table",
        "jp_unique_codes": len(jp_codes), "es_unique_codes": len(es_codes),
        "jp_missing_table_codes": [f"{code:04X}" for code in jp_codes if code not in jp_table],
        "es_missing_table_codes": [f"{code:04X}" for code in es_codes if code not in es_table],
        "mapping_differences": [
            {"code": f"{code:04X}", "jp": jp_table.get(code), "es": es_table.get(code)}
            for code in all_codes if jp_table.get(code) != es_table.get(code)
        ],
        "jp_atlases": jp_atlases,
        "es_atlases": es_atlases,
        "comparable_glyph_slots": len(comparable),
        "changed_glyph_slots": len(changed_glyphs),
        "changed_glyph_codes": [f"{code:04X}" for code in changed_glyphs],
        "jp_used_changed_glyph_codes": [f"{code:04X}" for code in jp_codes if code in changed_glyphs],
        "jp_used_preserved_glyph_codes": [f"{code:04X}" for code in jp_codes if code not in changed_glyphs],
        "jp_pim2_containers": pim2_containers(ROOT / "extracted" / "jp"),
        "es_pim2_containers": pim2_containers(ROOT / "extracted" / "es"),
    }
    write_json(args.output, report)
    print(f"JP codes={len(jp_codes)} ES codes={len(es_codes)} -> {args.output}")


if __name__ == "__main__":
    main()
