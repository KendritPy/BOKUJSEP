#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import posixpath
import shutil
import sys
from pathlib import Path, PurePosixPath

import pycdlib

from common import find_unique, hash_file, parse_sfo, write_json


ROOT = Path(__file__).resolve().parents[1]
KNOWN_JP_MD5 = "B4D363D59CB87E25AB76AFC5384CCA31"


def clean_component(value: str) -> str:
    return value.split(";", 1)[0].rstrip(".") or "_"


def extract_iso(iso_path: Path, output: Path, force: bool) -> None:
    marker = output / ".complete"
    if marker.exists() and not force:
        return
    if output.exists() and force:
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    iso = pycdlib.PyCdlib()
    iso.open(str(iso_path))
    try:
        for directory, _directories, filenames in iso.walk(iso_path="/"):
            for filename in filenames:
                source = posixpath.join(directory, filename)
                parts = [clean_component(part) for part in PurePosixPath(source).parts if part != "/"]
                destination = output.joinpath(*parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                iso.get_file_from_iso(local_path=str(destination), iso_path=source)
    finally:
        iso.close()
    marker.write_text("complete\n", encoding="ascii")


def load_boku_tools():
    source = ROOT / "external" / "boku-korean-tools" / "tools" / "boku_tools.py"
    if not source.exists():
        raise RuntimeError("missing Korean tools; run scripts/bootstrap.ps1")
    spec = importlib.util.spec_from_file_location("boku_tools", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract one Boku PSP ISO and its CDIMG archive")
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--edition", choices=("jp", "es"), required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    iso_path = args.iso.resolve()
    if not iso_path.is_file():
        raise SystemExit(f"ISO not found: {iso_path}")
    iso_root = ROOT / "extracted" / args.edition / "iso"
    cdimg_root = ROOT / "extracted" / args.edition / "cdimg"
    extract_iso(iso_path, iso_root, args.force)

    sfo_path = iso_root / "PSP_GAME" / "PARAM.SFO"
    if not sfo_path.is_file():
        sfo_path = find_unique(iso_root, "PARAM.SFO")
    sfo = parse_sfo(sfo_path)
    game_id = str(sfo.get("DISC_ID", "")).replace("-", "")
    if game_id and game_id != "UCJS10038":
        raise SystemExit(f"unexpected DISC_ID {sfo.get('DISC_ID')!r}; expected UCJS10038")

    idx_path = find_unique(iso_root, "cdimg.idx")
    img_path = find_unique(iso_root, "cdimg0.img")
    boku = load_boku_tools()
    if not (cdimg_root / ".complete").exists() or args.force:
        if cdimg_root.exists() and args.force:
            shutil.rmtree(cdimg_root)
        entries = boku.parse_index(idx_path)
        boku.extract_cd(entries, img_path, cdimg_root)
        (cdimg_root / ".complete").write_text("complete\n", encoding="ascii")

    hashes = hash_file(iso_path)
    eboot_path = iso_root / "PSP_GAME" / "SYSDIR" / "EBOOT.BIN"
    if not eboot_path.is_file():
        eboot_path = find_unique(iso_root, "EBOOT.BIN")
    report = {
        "edition": args.edition,
        "source": str(iso_path),
        "size": iso_path.stat().st_size,
        "hashes": hashes,
        "known_clean_jp_md5_match": args.edition == "jp" and hashes["md5"] == KNOWN_JP_MD5,
        "sfo": sfo,
        "paths": {"sfo": str(sfo_path), "cdimg_idx": str(idx_path), "cdimg_img": str(img_path)},
        "component_hashes": {
            "EBOOT.BIN": hash_file(eboot_path),
            "cdimg.idx": hash_file(idx_path),
            "cdimg0.img": hash_file(img_path),
        },
    }
    write_json(ROOT / "analysis" / args.edition / "input.json", report)
    print(f"{args.edition}: {sfo.get('DISC_ID', 'unknown')} SHA256={hashes['sha256']}")


if __name__ == "__main__":
    main()
