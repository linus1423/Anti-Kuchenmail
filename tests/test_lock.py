import subprocess
import unittest
from unittest import mock

from guard.lock import lock_screen


def result(code):
    return subprocess.CompletedProcess([], code, stdout="", stderr="fehler")


class LockTest(unittest.TestCase):
    def test_loginctl_success(self):
        run = mock.Mock(return_value=result(0))
        self.assertTrue(lock_screen(run=run))
        self.assertEqual(run.call_args_list[0].args[0], ["loginctl", "lock-session"])
        self.assertEqual(run.call_count, 1)

    def test_falls_back_to_dbus(self):
        run = mock.Mock(side_effect=[result(1), result(0)])
        with self.assertLogs("kuchenmail_guard", "WARNING"):
            self.assertTrue(lock_screen(run=run))
        self.assertEqual(run.call_args_list[1].args[0][0], "gdbus")

    def test_missing_commands_return_false(self):
        run = mock.Mock(side_effect=FileNotFoundError("weg"))
        with self.assertLogs("kuchenmail_guard", "ERROR"):
            self.assertFalse(lock_screen(run=run))


if __name__ == "__main__":
    unittest.main()
