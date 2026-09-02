#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from known_line_swap_probe import load_atlas


ROOT = Path(__file__).resolve().parents[1]


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
