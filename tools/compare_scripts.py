#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from common import write_json


ROOT = Path(__file__).resolve().parents[1]


def stable_id(item: dict[str, Any]) -> str:
    identity = "|".join(str(item.get(k, "")) for k in (
        "script", "pack_index", "pack_member", "dialog_id", "block_index", "element_index", "key"
    ))
    return "dlg_" + hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16]


def index_unique(items: set[int], records: list[dict[str, Any]], key: Callable[[dict[str, Any]], tuple]) -> dict[tuple, int]:
    grouped: dict[tuple, list[int]] = defaultdict(list)
    for index in items:
        grouped[key(records[index])].append(index)
    return {value: indices[0] for value, indices in grouped.items() if len(indices) == 1}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a conservative structural JP/ES dialogue correspondence")
    parser.add_argument("--jp", type=Path, default=ROOT / "data" / "jp" / "dialogue.json")
    parser.add_argument("--es", type=Path, default=ROOT / "data" / "es" / "dialogue.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "bilingual" / "dialogue_pairs.json")
    parser.add_argument("--report", type=Path, default=ROOT / "analysis" / "diffs" / "dialogue_mapping.json")
    args = parser.parse_args()
    jp = json.loads(args.jp.read_text(encoding="utf-8"))
    es = json.loads(args.es.read_text(encoding="utf-8"))
    remaining_jp, remaining_es = set(range(len(jp))), set(range(len(es)))
    matches: list[tuple[int, int, float, str]] = []

    strategies = [
        (lambda r: tuple(r.get(k) for k in ("script", "pack_index", "pack_member", "dialog_id", "block_index", "element_index", "key")), 1.0, "full_structural_key"),
        (lambda r: tuple(r.get(k) for k in ("script", "pack_member", "dialog_id", "block_index", "element_index", "key")), 0.99, "structural_key_shifted_pack_index"),
        (lambda r: tuple(r.get(k) for k in ("script", "pack_index", "pack_member", "dialog_id", "block_index", "element_index")), 0.98, "structural_position"),
        (lambda r: tuple(r.get(k) for k in ("script", "pack_member", "dialog_id", "key")), 0.90, "logical_key"),
    ]
    for key, confidence, method in strategies:
        left = index_unique(remaining_jp, jp, key)
        right = index_unique(remaining_es, es, key)
        for identity in sorted(left.keys() & right.keys(), key=repr):
            j, e = left[identity], right[identity]
            matches.append((j, e, confidence, method))
            remaining_jp.remove(j)
            remaining_es.remove(e)

    pairs = []
    for j, e, confidence, method in sorted(matches, key=lambda match: match[0]):
        left, right = jp[j], es[e]
        pairs.append({
            "id": stable_id(left),
            "script": left.get("script"),
            "pack_index": left.get("pack_index"),
            "pack_member": left.get("pack_member"),
            "dialog_id": left.get("dialog_id"),
            "block_index": left.get("block_index"),
            "element_index": left.get("element_index"),
            "key": left.get("key"),
            "jp": {"raw": left.get("raw_hex"), "decoded": left.get("text"), "text_offset": left.get("text_offset")},
            "es": {"raw": right.get("raw_hex"), "decoded": right.get("text"), "text_offset": right.get("text_offset")},
            "confidence": confidence,
            "mapping_method": method,
        })
    summary = {
        "jp_records": len(jp), "es_records": len(es), "paired": len(pairs),
        "exact_structural_matches": sum(method == "full_structural_key" for *_rest, method in matches),
        "ambiguous_or_unmatched_jp": len(remaining_jp),
        "ambiguous_or_unmatched_es": len(remaining_es),
        "coverage_jp": len(pairs) / len(jp) if jp else 0.0,
        "coverage_es": len(pairs) / len(es) if es else 0.0,
    }
    write_json(args.output, pairs)
    write_json(args.report, {
        "summary": summary,
        "unmatched_jp": [jp[i] for i in sorted(remaining_jp)],
        "unmatched_es": [es[i] for i in sorted(remaining_es)],
    })
    print(summary)


if __name__ == "__main__":
    main()
