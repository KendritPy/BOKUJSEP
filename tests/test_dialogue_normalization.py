from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from live_dialogue_probe import normalize_text as live_normalize  # noqa: E402
from pattern_dialogue_probe import normalize_text as pattern_normalize  # noqa: E402


class DialogueNormalizationTests(unittest.TestCase):
    def test_spanish_full_width_separator_is_searchable(self) -> None:
        source = "Ｔぉａ：\nＬａ「ｃｅｎａ「ｑｕｅ「ｈｅ「ｐｒｅｐａｒａｄｏ"
        expected = "tぉa la cena que he preparado"
        self.assertEqual(live_normalize(source), expected)
        self.assertEqual(pattern_normalize(source), expected)


if __name__ == "__main__":
    unittest.main()
