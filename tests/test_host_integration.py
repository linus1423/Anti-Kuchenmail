"""Startet den echten Host als Subprozess, mit gefälschtem zenity und loginctl im PATH."""

import json
import os
import struct
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = ROOT / "bin" / "kuchenmail-guard-host"


def frame(obj) -> bytes:
    data = json.dumps(obj).encode()
    return struct.pack("=I", len(data)) + data


class HostProcess:
    def __init__(self, zenity_exit: int):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        fake_bin = base / "bin"
        fake_bin.mkdir()
        for name, code in (("zenity", zenity_exit), ("loginctl", 0)):
            script = fake_bin / name
            script.write_text(f"#!/bin/sh\necho \"$0 $*\" >> {base}/calls.log\nexit {code}\n")
            script.chmod(0o755)
        env = {
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "HOME": str(base / "home"),
            "XDG_STATE_HOME": str(base / "state"),
            "XDG_CONFIG_HOME": str(base / "config"),
        }
        self.base = base
        self.proc = subprocess.Popen([str(HOST)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)

    def ask(self, message: dict) -> dict:
        self.proc.stdin.write(frame(message))
        self.proc.stdin.flush()
        (length,) = struct.unpack("=I", self.proc.stdout.read(4))
        return json.loads(self.proc.stdout.read(length))

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=10)
        self.proc.stdout.close()
        self.tmp.cleanup()


CAKE = {
    "type": "before_send", "client": "gmail", "subject": "Kuchen",
    "plain_text": "Ich bringe morgen Kuchen mit.", "recipients": ["team@firma.example"],
}


class HostIntegrationTest(unittest.TestCase):
    def test_ping_normal_mail_and_errors(self):
        host = HostProcess(zenity_exit=1)
        try:
            self.assertTrue(host.ask({"type": "ping"})["ok"])
            start = time.perf_counter()
            response = host.ask({**CAKE, "subject": "Bericht", "plain_text": "Anbei der Bericht.", "id": "x"})
            self.assertLess(time.perf_counter() - start, 0.1)
            self.assertEqual((response["action"], response["id"]), ("send", "x"))
            self.assertEqual(host.ask({"type": "?"})["error"], "unknown_type")
            self.assertEqual(host.ask({"type": "before_send", "client": "x"})["error"], "invalid_message")
        finally:
            host.close()

    def test_cake_mail_cancelled_in_dialog(self):
        host = HostProcess(zenity_exit=1)
        try:
            self.assertEqual(host.ask(CAKE)["action"], "cancel")
            calls = (host.base / "calls.log").read_text()
            self.assertIn("--hide-text", calls)
            attempts = (host.base / "state" / "kuchenmail-guard" / "attempts.jsonl").read_text()
            self.assertEqual(json.loads(attempts)["outcome"], "cancelled")
            self.assertTrue((host.base / "state" / "kuchenmail-guard" / "guard.log").exists())
        finally:
            host.close()

    def test_dialog_timeout_cancels(self):
        host = HostProcess(zenity_exit=5)
        try:
            self.assertEqual(host.ask(CAKE)["action"], "cancel")
        finally:
            host.close()

    def test_exits_cleanly_on_eof(self):
        host = HostProcess(zenity_exit=1)
        host.proc.stdin.close()
        self.assertEqual(host.proc.wait(timeout=10), 0)
        host.proc.stdout.close()
        host.tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
