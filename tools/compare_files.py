#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import hash_file, write_json


ROOT = Path(__file__).resolve().parents[1]


def inventory(root: Path) -> dict[str, Path]:
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file() and p.name != ".complete"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a complete JP/ES file-level diff")
    parser.add_argument("--jp", type=Path, default=ROOT / "extracted" / "jp")
    parser.add_argument("--es", type=Path, default=ROOT / "extracted" / "es")
    parser.add_argument("--output", type=Path, default=ROOT / "analysis" / "diffs" / "file_diff.json")
    args = parser.parse_args()
    jp, es = inventory(args.jp), inventory(args.es)
    rows = []
    for relative in sorted(jp.keys() | es.keys()):
        left, right = jp.get(relative), es.get(relative)
        left_hash = hash_file(left, ("sha256",))["sha256"] if left else None
        right_hash = hash_file(right, ("sha256",))["sha256"] if right else None
        rows.append({
            "path": relative,
            "jp_size": left.stat().st_size if left else None,
            "es_size": right.stat().st_size if right else None,
            "jp_sha256": left_hash,
            "es_sha256": right_hash,
            "identical": left_hash is not None and left_hash == right_hash,
            "status": "both" if left and right else "jp_only" if left else "es_only",
        })
    summary = {
        "jp_files": len(jp), "es_files": len(es), "compared_paths": len(rows),
        "identical": sum(row["identical"] for row in rows),
        "different": sum(row["status"] == "both" and not row["identical"] for row in rows),
        "jp_only": sum(row["status"] == "jp_only" for row in rows),
        "es_only": sum(row["status"] == "es_only" for row in rows),
    }
    write_json(args.output, {"summary": summary, "files": rows})
    print(summary)


if __name__ == "__main__":
    main()
