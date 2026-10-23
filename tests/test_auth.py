import subprocess
import unittest
from unittest import mock

from guard import auth
from guard.auth import AuthUnavailable, Outcome, ask_password_zenity, confirm_send


class ConfirmSendTest(unittest.TestCase):
    def run_with(self, answers, correct="richtig"):
        answers = iter(answers)
        asked = []

        def ask(subject, attempt):
            asked.append(attempt)
            return next(answers)

        outcome = confirm_send("Kuchen", ask=ask, check=lambda pw: pw == correct)
        return outcome, asked

    def test_correct_password_releases(self):
        self.assertEqual(self.run_with(["richtig"]), (Outcome.RELEASED, [1]))

    def test_correct_on_third_try_releases(self):
        self.assertEqual(self.run_with(["a", "b", "richtig"]), (Outcome.RELEASED, [1, 2, 3]))

    def test_cancel_returns_cancelled(self):
        self.assertEqual(self.run_with([None]), (Outcome.CANCELLED, [1]))

    def test_cancel_after_wrong_password(self):
        self.assertEqual(self.run_with(["a", None]), (Outcome.CANCELLED, [1, 2]))

    def test_three_wrong_passwords_fail(self):
        self.assertEqual(self.run_with(["a", "b", "c", "richtig"]), (Outcome.FAILED, [1, 2, 3]))

    def test_empty_password_counts_as_wrong_without_pam_call(self):
        check = mock.Mock(return_value=True)
        outcome = confirm_send("x", ask=lambda s, a: "", check=check)
        self.assertEqual(outcome, Outcome.FAILED)
        check.assert_not_called()


class ZenityTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(auth.shutil, "which", return_value="/usr/bin/zenity")
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_run(self, returncode=0, stdout=""):
        return mock.Mock(return_value=subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=""))

    def test_returns_password_without_newline(self):
        run = self.fake_run(stdout="geheim\n")
        self.assertEqual(ask_password_zenity("Kuchen", 1, run=run), "geheim")
        args = run.call_args.args[0]
        self.assertIn("--hide-text", args)
        self.assertIn("--timeout=120", args)

    def test_password_with_spaces_is_kept(self):
        self.assertEqual(ask_password_zenity("x", 1, run=self.fake_run(stdout=" a b \n")), " a b ")

    def test_cancel_and_timeout_return_none(self):
        self.assertIsNone(ask_password_zenity("x", 1, run=self.fake_run(returncode=1)))
        self.assertIsNone(ask_password_zenity("x", 1, run=self.fake_run(returncode=5)))

    def test_subject_markup_is_escaped(self):
        run = self.fake_run(stdout="x\n")
        ask_password_zenity("<b>Kuchen</b> & Torte", 2, run=run)
        text = run.call_args.args[0][run.call_args.args[0].index("--text") + 1]
        self.assertIn("&lt;b&gt;Kuchen&lt;/b&gt; &amp; Torte", text)
        self.assertIn("Versuch 2 von 3", text)

    def test_missing_zenity_raises(self):
        with mock.patch.object(auth.shutil, "which", return_value=None):
            with self.assertRaises(AuthUnavailable):
                ask_password_zenity("x", 1)


if __name__ == "__main__":
    unittest.main()
