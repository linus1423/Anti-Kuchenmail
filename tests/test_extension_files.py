import json
import unittest
from pathlib import Path

EXT = Path(__file__).resolve().parent.parent / "extensions"


class ExtensionFilesTest(unittest.TestCase):
    def test_native_connection_is_identical_in_both_extensions(self):
        self.assertEqual(
            (EXT / "thunderbird" / "native.js").read_text(encoding="utf-8"),
            (EXT / "webmail" / "native.js").read_text(encoding="utf-8"),
            "native.js in beiden Erweiterungen gleich halten",
        )

    def test_ids_match_native_manifest(self):
        allowed = json.loads((EXT.parent / "packaging" / "native-manifest.json.in").read_text())["allowed_extensions"]
        for name in ("thunderbird", "webmail"):
            manifest = json.loads((EXT / name / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn(manifest["browser_specific_settings"]["gecko"]["id"], allowed)

    def test_referenced_scripts_exist(self):
        manifest = json.loads((EXT / "webmail" / "manifest.json").read_text(encoding="utf-8"))
        files = list(manifest["background"]["scripts"])
        for entry in manifest["content_scripts"]:
            files += entry["js"]
        files.append(manifest["options_ui"]["page"])
        background = (EXT / "webmail" / "background.js").read_text(encoding="utf-8")
        for script in ("shared/flow.js", "shared/dom.js", "adapters/roundcube.js"):
            self.assertIn(script, background)
            files.append(script)
        for file in files:
            self.assertTrue((EXT / "webmail" / file).exists(), file)


if __name__ == "__main__":
    unittest.main()
