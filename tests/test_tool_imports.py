from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))


class SupportedToolImportTests(unittest.TestCase):
    def test_all_supported_tool_modules_import(self) -> None:
        """Evita que una limpieza deje imports hacia herramientas eliminadas."""
        modules = sorted(
            path.stem
            for path in TOOLS.glob("*.py")
            if path.name != "__init__.py"
        )
        self.assertTrue(modules)
        for module_name in modules:
            with self.subTest(module=module_name):
                importlib.import_module(module_name)


if __name__ == "__main__":
    unittest.main()
