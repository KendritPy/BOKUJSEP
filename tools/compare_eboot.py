#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JP = ROOT / "extracted/jp/iso/PSP_GAME/SYSDIR/BOOT.BIN"
DEFAULT_ES = ROOT / "extracted/es/iso/PSP_GAME/SYSDIR/EBOOT.BIN"
DEFAULT_OUTPUT = ROOT / "analysis/diffs/eboot_diff.json"
PSP_TEXT_RUNTIME_ADDRESS = 0x08804000
RUNTIME_LOAD_BIAS = PSP_TEXT_RUNTIME_ADDRESS


@dataclass(frozen=True)
class Section:
    name: str
    section_type: int
    flags: int
    address: int
    offset: int
    size: int
    data: bytes


def parse_elf(path: Path) -> tuple[bytes, dict[str, Section]]:
    data = path.read_bytes()
    if data[:7] != b"\x7fELF\x01\x01\x01":
        raise ValueError(f"not a 32-bit little-endian ELF: {path}")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", data, 0)
    section_offset = header[6]
    section_entry_size = header[11]
    section_count = header[12]
    string_index = header[13]
    raw = [
        struct.unpack_from("<IIIIIIIIII", data, section_offset + i * section_entry_size)
        for i in range(section_count)
    ]
    string_header = raw[string_index]
    strings = data[string_header[4] : string_header[4] + string_header[5]]
    sections: dict[str, Section] = {}
    for item in raw:
        name_offset, section_type, flags, address, offset, size, *_ = item
        end = strings.find(b"\0", name_offset)
        name = strings[name_offset:end].decode("ascii", errors="replace")
        if not name:
            continue
        sections[name] = Section(
            name=name,
            section_type=section_type,
            flags=flags,
            address=address,
            offset=offset,
            size=size,
            data=data[offset : offset + size],
        )
    return data, sections


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def changed_byte_count(left: bytes, right: bytes) -> int:
    return sum(a != b for a, b in zip(left, right)) + abs(len(left) - len(right))


def direct_edges(section: Section, target_start: int, target_end: int) -> list[dict[str, object]]:
    edges: list[dict[str, object]] = []
    for offset in range(0, len(section.data) - 3, 4):
        word = struct.unpack_from("<I", section.data, offset)[0]
        opcode = word >> 26
        if opcode not in (2, 3):
            continue
        address = section.address + offset
        target = ((address + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        if target_start <= target < target_end:
            edges.append(
                {
                    "source_offset": f"0x{address:08X}",
                    "source_guest": f"0x{RUNTIME_LOAD_BIAS + address:08X}",
                    "kind": "jal" if opcode == 3 else "j",
                    "target_offset": f"0x{target:08X}",
                    "target_guest": f"0x{RUNTIME_LOAD_BIAS + target:08X}",
                    "word": f"0x{word:08X}",
                }
            )
    return edges


def build_report(jp_path: Path, es_path: Path) -> dict[str, object]:
    jp_data, jp_sections = parse_elf(jp_path)
    es_data, es_sections = parse_elf(es_path)
    section_report: list[dict[str, object]] = []
    for name in sorted(set(jp_sections) | set(es_sections)):
        jp = jp_sections.get(name)
        es = es_sections.get(name)
        section_report.append(
            {
                "name": name,
                "jp": None if jp is None else {
                    "address": f"0x{jp.address:08X}", "offset": f"0x{jp.offset:08X}",
                    "size": jp.size, "flags": f"0x{jp.flags:X}", "sha256": digest(jp.data),
                },
                "es": None if es is None else {
                    "address": f"0x{es.address:08X}", "offset": f"0x{es.offset:08X}",
                    "size": es.size, "flags": f"0x{es.flags:X}", "sha256": digest(es.data),
                },
                "changed_bytes": None if jp is None or es is None else changed_byte_count(jp.data, es.data),
            }
        )

    injected = es_sections[".comment"]
    edges = direct_edges(es_sections[".text"], injected.address, injected.address + injected.size)
    return {
        "jp": {"path": str(jp_path), "size": len(jp_data), "sha256": digest(jp_data)},
        "es": {"path": str(es_path), "size": len(es_data), "sha256": digest(es_data)},
        "same_size": len(jp_data) == len(es_data),
        "sections": section_report,
        "spanish_injected_region": {
            "section": ".comment",
            "offset_start": f"0x{injected.offset:08X}",
            "offset_end": f"0x{injected.offset + injected.size:08X}",
            "module_start": f"0x{injected.address:08X}",
            "module_end": f"0x{injected.address + injected.size:08X}",
            "guest_start": f"0x{RUNTIME_LOAD_BIAS + injected.address:08X}",
            "guest_end": f"0x{RUNTIME_LOAD_BIAS + injected.address + injected.size:08X}",
            "size": injected.size,
            "flags": f"0x{injected.flags:X}",
        },
        "direct_text_edges_into_injected_region": edges,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare the clean JP ELF with the Spanish patched ELF")
    parser.add_argument("--jp", type=Path, default=DEFAULT_JP)
    parser.add_argument("--es", type=Path, default=DEFAULT_ES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.jp, args.es)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Direct patched edges: {len(report['direct_text_edges_into_injected_region'])}")


if __name__ == "__main__":
    main()
