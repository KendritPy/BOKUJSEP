#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_atlas(edition: str, atlas_index: int = 0) -> bytes:
    """Extract one raw PIM2 atlas without depending on diagnostic probes."""
    source = ROOT / "external/boku-korean-tools/tools/boku_tools.py"
    spec = importlib.util.spec_from_file_location(f"boku_tools_assets_{edition}", source)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    startup = ROOT / f"extracted/{edition}/cdimg/01startup/startup.bin.gzx"
    payload = gzip.decompress(startup.read_bytes()[4:])
    startup_entries = module.parse_pack_entries(payload, with_names=True)
    font_entry = next(
        (entry for entry in startup_entries if entry["name"].lower() == "font.bin"),
        None,
    )
    if font_entry is None:
        raise RuntimeError(f"font.bin not found in {startup}")
    font_pack = payload[font_entry["offset"] : font_entry["offset"] + font_entry["size"]]
    images = []
    for entry in module.parse_pack_entries(font_pack, with_names=False):
        image = font_pack[entry["offset"] : entry["offset"] + entry["size"]]
        if image.startswith(b"PIM2"):
            images.append(image)
    if atlas_index >= len(images):
        raise RuntimeError(f"font atlas {atlas_index} not found in {startup}")
    return images[atlas_index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export runtime font assets from the user's extracted ISOs")
    parser.add_argument("--output", type=Path, default=ROOT / "build/generated")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for edition in ("jp", "es"):
        output = args.output / f"{edition}_atlas0.pim"
        output.write_bytes(load_atlas(edition))
        print(f"wrote {output}")


if __name__ == "__main__":
    main()
