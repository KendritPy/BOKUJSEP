from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Iterable


def hash_file(path: Path, algorithms: Iterable[str] = ("md5", "sha256")) -> dict[str, str]:
    states = {name: hashlib.new(name) for name in algorithms}
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            for state in states.values():
                state.update(chunk)
    return {name: state.hexdigest().upper() for name, state in states.items()}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_unique(root: Path, filename: str) -> Path:
    matches = [p for p in root.rglob("*") if p.is_file() and p.name.casefold() == filename.casefold()]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {filename} below {root}, found {len(matches)}")
    return matches[0]


def parse_sfo(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"\x00PSF":
        raise ValueError(f"not a PARAM.SFO: {path}")
    _magic, version, key_off, data_off, count = struct.unpack_from("<4sIIII", data, 0)
    result: dict[str, Any] = {"_version": version}
    for index in range(count):
        entry = 20 + index * 16
        key_rel, fmt, used, _maximum, value_rel = struct.unpack_from("<HHIII", data, entry)
        key_end = data.index(0, key_off + key_rel)
        key = data[key_off + key_rel : key_end].decode("utf-8", errors="replace")
        raw = data[data_off + value_rel : data_off + value_rel + used]
        if fmt == 0x0404 and len(raw) >= 4:
            value: Any = struct.unpack_from("<I", raw)[0]
        elif fmt in (0x0004, 0x0204):
            value = raw.rstrip(b"\x00").decode("utf-8", errors="replace")
        else:
            value = raw.hex().upper()
        result[key] = value
    return result

