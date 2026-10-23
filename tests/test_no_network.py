"""N1: kein Netzwerk. Weder der Python-Teil noch die Erweiterungen dürfen Verbindungen aufbauen."""

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_MODULES = {"socket", "ssl", "http", "urllib", "smtplib", "imaplib", "poplib", "ftplib", "xmlrpc", "asyncio", "telnetlib"}
FORBIDDEN_COMMANDS = re.compile(r"\b(curl|wget|nc|ssh)\b")
FORBIDDEN_JS = re.compile(r"\b(fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\b")


class NoNetworkTest(unittest.TestCase):
    def test_python_does_not_import_network_modules(self):
        for path in sorted((ROOT / "guard").glob("*.py")) + sorted((ROOT / "bin").glob("*")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    with self.subTest(file=path.name, module=name):
                        self.assertNotIn(name.split(".")[0], FORBIDDEN_MODULES)

    def test_python_starts_no_network_tools(self):
        for path in (ROOT / "guard").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    with self.subTest(file=path.name, value=node.value[:40]):
                        self.assertIsNone(FORBIDDEN_COMMANDS.fullmatch(node.value))

    def test_extensions_make_no_requests(self):
        for path in sorted((ROOT / "extensions").rglob("*.js")):
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertIsNone(FORBIDDEN_JS.search(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
