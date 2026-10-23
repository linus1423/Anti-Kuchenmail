"""Installiert in ein temporäres Home-Verzeichnis und prüft das Ergebnis."""

import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("sh") and Path("/usr/bin/python3").exists(), "braucht sh und /usr/bin/python3")
class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        fake_bin = self.home / "fakebin"
        fake_bin.mkdir()
        # systemctl --user gibt es im Test nicht; Aufrufe protokollieren statt ausführen
        (fake_bin / "systemctl").write_text(f"#!/bin/sh\necho \"$*\" >> {self.home}/systemctl.log\n")
        (fake_bin / "systemctl").chmod(0o755)
        self.env = {
            "HOME": str(self.home),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "LANG": "C.UTF-8",
        }
        self.share = self.home / ".local/share/kuchenmail-guard"

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, name):
        return subprocess.run(["sh", str(ROOT / name)], env=self.env, capture_output=True, text=True, check=True)

    def test_install_creates_everything(self):
        self.run_script("install.sh")
        self.assertTrue((self.share / "guard" / "classifier.py").exists())
        self.assertFalse(list(self.share.rglob("__pycache__")))
        host = self.home / ".local/bin/kuchenmail-guard-host"
        self.assertTrue(host.is_symlink())

        for directory in (".mozilla/native-messaging-hosts", ".thunderbird/native-messaging-hosts"):
            manifest = json.loads((self.home / directory / "kuchenmail_guard.json").read_text())
            self.assertEqual(manifest["path"], str(self.share / "bin/kuchenmail-guard-host"))
            self.assertIn("thunderbird@kuchenmail-guard", manifest["allowed_extensions"])

        with zipfile.ZipFile(self.share / "kuchenmail-guard-thunderbird.xpi") as xpi:
            names = xpi.namelist()
        self.assertIn("manifest.json", names)
        self.assertIn("background.js", names)

        self.assertTrue((self.home / ".config/kuchenmail-guard/rules.toml").exists())

    def test_installed_host_answers_ping(self):
        self.run_script("install.sh")
        data = json.dumps({"type": "ping"}).encode()
        result = subprocess.run(
            [str(self.share / "bin/kuchenmail-guard-host")],
            input=struct.pack("=I", len(data)) + data,
            capture_output=True, env=self.env, timeout=20,
        )
        (length,) = struct.unpack("=I", result.stdout[:4])
        self.assertTrue(json.loads(result.stdout[4 : 4 + length])["ok"])

    def test_reinstall_keeps_own_rules(self):
        self.run_script("install.sh")
        rules = self.home / ".config/kuchenmail-guard/rules.toml"
        rules.write_text("threshold = 2.0\n")
        self.run_script("install.sh")
        self.assertEqual(rules.read_text(), "threshold = 2.0\n")

    def test_uninstall_removes_program_but_keeps_rules_and_log(self):
        self.run_script("install.sh")
        state = self.home / ".local/state/kuchenmail-guard"
        state.mkdir(parents=True)
        (state / "attempts.jsonl").write_text("{}\n")
        self.run_script("uninstall.sh")
        self.assertFalse(self.share.exists())
        self.assertFalse((self.home / ".local/bin/kuchenmail-guard-host").exists())
        self.assertFalse((self.home / ".mozilla/native-messaging-hosts/kuchenmail_guard.json").exists())
        self.assertTrue((self.home / ".config/kuchenmail-guard/rules.toml").exists())
        self.assertTrue((state / "attempts.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
