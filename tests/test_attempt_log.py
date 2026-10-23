import json
import stat
import tempfile
import unittest
from pathlib import Path

from guard.attempt_log import Attempt, AttemptLog
from guard.model import MailDraft, Verdict

DRAFT = MailDraft(
    client="gmail",
    subject="Kuchen!",
    plain_text="GEHEIMER MAILTEXT: Ich bringe morgen Kuchen mit.",
    html="<p>GEHEIMER MAILTEXT</p>",
    recipients=("team@firma.example",),
)
VERDICT = Verdict(suspicious=True, score=1.6, hits=("food:kuchen",))


class AttemptLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name) / "state" / "kuchenmail-guard"
        self.log = AttemptLog(self.directory)

    def tearDown(self):
        self.tmp.cleanup()

    def test_permissions_are_private(self):
        self.log.append(Attempt.new(DRAFT, VERDICT, "cancelled"))
        self.log.mark_notified([self.log.all()[0].id])
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.log.attempts_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.log.notified_path.stat().st_mode), 0o600)

    def test_entry_has_required_fields_but_no_mail_text(self):
        self.log.append(Attempt.new(DRAFT, VERDICT, "locked"))
        raw = self.log.attempts_path.read_text(encoding="utf-8")
        self.assertNotIn("GEHEIMER MAILTEXT", raw)
        entry = json.loads(raw)
        self.assertEqual(entry["subject"], "Kuchen!")
        self.assertEqual(entry["recipients"], ["team@firma.example"])
        self.assertEqual(entry["outcome"], "locked")
        self.assertEqual(entry["client"], "gmail")
        self.assertIn("T", entry["ts"])

    def test_pending_and_mark_notified(self):
        first = Attempt.new(DRAFT, VERDICT, "cancelled")
        second = Attempt.new(DRAFT, VERDICT, "released")
        self.log.append(first)
        self.log.append(second)
        self.assertEqual([a.id for a in self.log.pending()], [first.id, second.id])
        self.log.mark_notified([first.id])
        self.assertEqual([a.id for a in self.log.pending()], [second.id])
        self.assertEqual(len(self.log.all()), 2)

    def test_empty_log(self):
        self.assertEqual(self.log.all(), [])
        self.assertEqual(self.log.pending(), [])
        self.log.mark_notified([])
        self.assertFalse(self.directory.exists())

    def test_broken_lines_are_skipped(self):
        self.log.append(Attempt.new(DRAFT, VERDICT, "cancelled"))
        with self.log.attempts_path.open("a", encoding="utf-8") as fh:
            fh.write('{"halb": \n')
        self.assertEqual(len(self.log.all()), 1)

    def test_unknown_outcome_is_rejected(self):
        with self.assertRaises(ValueError):
            Attempt.new(DRAFT, VERDICT, "vielleicht")


if __name__ == "__main__":
    unittest.main()
