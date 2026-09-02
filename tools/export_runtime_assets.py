#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_boku_tools(edition: str):
    source = ROOT / "external/boku-korean-tools/tools/boku_tools.py"
    if not source.is_file():
        raise RuntimeError("Faltan las herramientas de Boku; ejecuta scripts/bootstrap.ps1 primero.")
    spec = importlib.util.spec_from_file_location(f"boku_tools_assets_{edition}", source)
    if not spec or not spec.loader:
        raise RuntimeError(f"No se pudo cargar {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_atlas(edition: str, atlas_index: int = 0) -> bytes:
    """Extrae un atlas PIM2 desde startup.bin.gzx de la edición indicada."""
    boku = load_boku_tools(edition)
    startup = ROOT / f"extracted/{edition}/cdimg/01startup/startup.bin.gzx"
    if not startup.is_file():
        raise RuntimeError(f"No se encontró el archivo de fuente extraído: {startup}")

    raw = startup.read_bytes()
    if len(raw) < 4:
        raise RuntimeError(f"Archivo GZX inválido o truncado: {startup}")
    payload = gzip.decompress(raw[4:])

    startup_entries = boku.parse_pack_entries(payload, with_names=True)
    font_entry = next(
        (item for item in startup_entries if item.get("name", "").lower() == "font.bin"),
        None,
    )
    if font_entry is None:
        raise RuntimeError(f"No se encontró font.bin dentro de {startup}")

    offset = font_entry["offset"]
    size = font_entry["size"]
    font_pack = payload[offset:offset + size]

    images: list[bytes] = []
    for entry in boku.parse_pack_entries(font_pack, with_names=False):
        image = font_pack[entry["offset"]:entry["offset"] + entry["size"]]
        if image.startswith(b"PIM2"):
            images.append(image)

    if atlas_index >= len(images):
        raise RuntimeError(
            f"Atlas PIM2 {atlas_index} no encontrado en la edición {edition}; "
            f"se detectaron {len(images)} atlas."
        )
    return images[atlas_index]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exporta las fuentes necesarias por el plugin desde las ISOs extraídas"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "build/generated")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    for edition in ("jp", "es"):
        output = args.output / f"{edition}_atlas0.pim"
        output.write_bytes(load_atlas(edition))
        print(f"escrito {output}")


if __name__ == "__main__":
    main()
