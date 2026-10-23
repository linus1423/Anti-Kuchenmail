"""N5: Notifier im Leerlauf < 50 MB RAM und < 1 % CPU (gemessen über /proc, nur Linux)."""

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rss_mb(pid: int) -> float:
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    raise AssertionError("VmRSS nicht gefunden")


def cpu_seconds(pid: int) -> float:
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")


@unittest.skipUnless(sys.platform.startswith("linux"), "nur unter Linux messbar")
class ResourceTest(unittest.TestCase):
    def test_idle_notifier_is_light(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_bin = Path(tmp) / "bin"
            fake_bin.mkdir()
            # gdbus monitor wartet im echten Leben auf Signale; hier einfach schlafen
            (fake_bin / "gdbus").write_text("#!/bin/sh\nexec sleep 60\n")
            (fake_bin / "gdbus").chmod(0o755)
            env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}", "XDG_STATE_HOME": tmp}
            proc = subprocess.Popen([str(ROOT / "bin" / "kuchenmail-guard-notifier")], env=env)
            try:
                time.sleep(1.0)  # Start abwarten
                cpu_start = cpu_seconds(proc.pid)
                time.sleep(2.0)
                cpu_used = cpu_seconds(proc.pid) - cpu_start
                self.assertIsNone(proc.poll(), "Notifier ist abgestürzt")
                self.assertLess(rss_mb(proc.pid), 50)
                self.assertLess(cpu_used / 2.0, 0.01)
            finally:
                proc.terminate()
                proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
