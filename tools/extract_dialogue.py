#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract raw/decoded dialogue with the proven Boku parser")
    parser.add_argument("--edition", choices=("jp", "es"), required=True)
    parser.add_argument("--table", type=Path, default=ROOT / "external" / "boku-pleonex" / "font" / "table.txt")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    source = ROOT / "external" / "boku-korean-tools" / "tools" / "boku_tools.py"
    spec = importlib.util.spec_from_file_location("boku_tools", source)
    if not spec or not spec.loader:
        raise SystemExit(f"cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    output = ROOT / "data" / args.edition / "dialogue.json"
    module.extract_scripts(ROOT / "extracted" / args.edition / "cdimg", args.table, output, args.limit)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
