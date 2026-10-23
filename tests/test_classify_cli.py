import contextlib
import io
import unittest

from guard.classify import main
from tests.helpers import CORPUS


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main([*args, "--rules", "/nonexistent/rules.toml"])
    return code, out.getvalue()


class CliTest(unittest.TestCase):
    def test_cake_mail_exit_code_1(self):
        code, out = run(str(CORPUS / "cake" / "01-de.eml"))
        self.assertEqual(code, 1)
        self.assertIn("KUCHENMAIL-VERDACHT", out)

    def test_normal_mail_exit_code_0(self):
        code, out = run(str(CORPUS / "normal" / "01-de.eml"))
        self.assertEqual(code, 0)
        self.assertIn("unauffällig", out)

    def test_missing_file_exit_code_2(self):
        code, _ = run("/nonexistent/mail.eml")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
