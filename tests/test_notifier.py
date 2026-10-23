import tempfile
import unittest
from pathlib import Path

from guard.attempt_log import Attempt, AttemptLog
from guard.model import MailDraft, Verdict
from guard.notifier import UNLOCK_SIGNAL, describe, notify_pending, run_forever, watch_unlocks

VERDICT = Verdict(True, 1.6)


def attempt(outcome="cancelled", subject="Kuchen!", recipients=("team@firma.example",)):
    return Attempt.new(MailDraft("gmail", subject, "", None, recipients), VERDICT, outcome)


class NotifierTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = AttemptLog(Path(self.tmp.name))
        self.sent = []

    def tearDown(self):
        self.tmp.cleanup()

    def send(self, title, body):
        self.sent.append((title, body))

    def test_each_attempt_is_notified_exactly_once(self):
        self.log.append(attempt())
        self.log.append(attempt("locked"))
        self.assertEqual(notify_pending(self.log, self.send), 2)
        self.assertEqual(notify_pending(self.log, self.send), 0)
        self.assertEqual(len(self.sent), 2)
        self.assertEqual(self.log.pending(), [])

    def test_released_attempts_are_marked_but_not_shown(self):
        self.log.append(attempt("released"))
        self.assertEqual(notify_pending(self.log, self.send), 0)
        self.assertEqual(self.sent, [])
        self.assertEqual(self.log.pending(), [])

    def test_many_attempts_are_summarized(self):
        for _ in range(5):
            self.log.append(attempt())
        self.assertEqual(notify_pending(self.log, self.send), 1)
        self.assertEqual(self.sent[0][0], "5 Kuchenmails abgefangen")

    def test_description_contains_time_client_subject_and_outcome(self):
        text = describe(attempt("locked", recipients=("a@x.example", "b@x.example", "c@x.example")))
        self.assertIn("Gmail", text)
        self.assertIn("„Kuchen!“ an a@x.example, b@x.example …", text)
        self.assertIn("Bildschirm gesperrt", text)

    def test_only_unlock_signal_triggers(self):
        calls = []
        lines = [
            "/org/gnome/ScreenSaver: org.gnome.ScreenSaver.ActiveChanged (true,)\n",
            f"/org/gnome/ScreenSaver: {UNLOCK_SIGNAL}\n",
            "/org/gnome/ScreenSaver: org.gnome.ScreenSaver.WakeUpScreen ()\n",
        ]
        watch_unlocks(lines, lambda: calls.append(1))
        self.assertEqual(calls, [1])

    def test_run_forever_notifies_on_start_and_on_unlock(self):
        self.log.append(attempt())
        log = self.log

        class FakeMonitor:
            def __init__(self, *args, **kwargs):
                log.append(attempt(subject="Zweiter Versuch"))
                self.stdout = [f"x: {UNLOCK_SIGNAL}\n"]

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        run_forever(self.log, send=self.send, popen=FakeMonitor, sleep=lambda s: None, rounds=1)
        self.assertEqual([body.split("\n")[1] for _, body in self.sent], ["„Kuchen!“ an team@firma.example", "„Zweiter Versuch“ an team@firma.example"])


if __name__ == "__main__":
    unittest.main()
