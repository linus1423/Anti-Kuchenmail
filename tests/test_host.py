import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

from guard import auth
from guard.attempt_log import AttemptLog
from guard.host import Guard, ProtocolError, read_message, serve, write_message
from tests.helpers import default_rules

CAKE = {
    "type": "before_send",
    "client": "thunderbird",
    "subject": "Kuchen",
    "plain_text": "Ich bringe morgen Kuchen mit.",
    "recipients": ["team@firma.example"],
}
NORMAL = {**CAKE, "subject": "Bericht", "plain_text": "Anbei der Bericht."}


def frame(obj) -> bytes:
    data = json.dumps(obj).encode()
    return struct.pack("=I", len(data)) + data


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = AttemptLog(Path(self.tmp.name))
        self.locks = 0
        self.outcome = auth.Outcome.CANCELLED
        self.rules = default_rules()

    def tearDown(self):
        self.tmp.cleanup()

    def lock(self):
        self.locks += 1
        return True

    def guard(self, confirm=None, rules=None):
        return Guard(
            rules_loader=lambda: rules or self.rules,
            attempt_log=self.log,
            confirm=confirm or (lambda subject: self.outcome),
            lock=self.lock,
        )

    def test_ping(self):
        response = self.guard().handle({"type": "ping", "id": 7})
        self.assertTrue(response["ok"])
        self.assertEqual(response["id"], 7)

    def test_normal_mail_is_sent_without_dialog(self):
        def confirm(_):
            raise AssertionError("kein Dialog erwartet")

        response = self.guard(confirm=confirm).handle(NORMAL)
        self.assertEqual(response["action"], "send")
        self.assertEqual(self.log.all(), [])

    def test_released_is_sent_and_logged(self):
        self.outcome = auth.Outcome.RELEASED
        self.assertEqual(self.guard().handle(CAKE)["action"], "send")
        self.assertEqual([a.outcome for a in self.log.all()], ["released"])

    def test_cancelled_keeps_draft(self):
        self.assertEqual(self.guard().handle(CAKE)["action"], "cancel")
        self.assertEqual([a.outcome for a in self.log.all()], ["cancelled"])
        self.assertEqual(self.locks, 0)

    def test_failed_discards_and_locks(self):
        self.outcome = auth.Outcome.FAILED
        self.assertEqual(self.guard().handle(CAKE)["action"], "discard")
        self.assertEqual([a.outcome for a in self.log.all()], ["locked"])
        self.assertEqual(self.locks, 1)

    def test_missing_dialog_cancels(self):
        def confirm(_):
            raise auth.AuthUnavailable("zenity fehlt")

        with self.assertLogs("kuchenmail_guard", "ERROR"):
            response = self.guard(confirm=confirm).handle(CAKE)
        self.assertEqual(response["action"], "cancel")
        self.assertEqual(response["reason"], "auth_unavailable")

    def test_check_without_lock_on_detect(self):
        response = self.guard().handle({**CAKE, "type": "check", "draft_id": "a"})
        self.assertEqual((response["suspicious"], response["locked"]), (True, False))
        self.assertEqual(self.locks, 0)

    def test_check_with_lock_on_detect_locks_once_per_draft(self):
        from dataclasses import replace

        rules = replace(self.rules, lock_on_detect=True)
        guard = self.guard(rules=rules)
        check = {**CAKE, "type": "check", "draft_id": "a"}
        self.assertTrue(guard.handle(check)["locked"])
        self.assertFalse(guard.handle(check)["locked"])
        self.assertTrue(guard.handle({**check, "draft_id": "b"})["locked"])
        self.assertEqual(self.locks, 2)
        self.assertEqual([a.outcome for a in self.log.all()], ["locked_on_detect"] * 2)

    def test_invalid_messages(self):
        guard = self.guard()
        cases = [
            {"type": "before_send", "client": "outlook", "recipients": "nicht-liste"},
            {"type": "before_send", "client": "unbekannt"},
            {"type": "before_send", "client": "gmail", "subject": 5},
        ]
        for message in cases:
            with self.subTest(message=message), self.assertLogs("kuchenmail_guard", "WARNING"):
                self.assertEqual(guard.handle(message)["error"], "invalid_message")
        self.assertEqual(guard.handle({"type": "tanzen"})["error"], "unknown_type")


class ProtocolTest(unittest.TestCase):
    def test_roundtrip(self):
        out = io.BytesIO()
        write_message(out, {"ä": "ö"})
        self.assertEqual(read_message(io.BytesIO(out.getvalue())), {"ä": "ö"})

    def test_eof_returns_none(self):
        self.assertIsNone(read_message(io.BytesIO(b"")))

    def test_truncated_and_invalid_input(self):
        for raw in (b"\x05\x00", struct.pack("=I", 10) + b"{}", struct.pack("=I", 3) + b"abc", frame([1, 2])):
            with self.subTest(raw=raw), self.assertRaises(ProtocolError):
                read_message(io.BytesIO(raw))

    def test_too_large_is_rejected(self):
        with self.assertRaises(ProtocolError):
            read_message(io.BytesIO(struct.pack("=I", 100 * 1024 * 1024)))

    def test_serve_answers_each_message_in_order(self):
        guard = Guard(rules_loader=default_rules, attempt_log=AttemptLog(Path("/nonexistent")), confirm=None, lock=None)
        stdin = io.BytesIO(frame({"type": "ping", "id": 1}) + frame({**NORMAL, "id": 2}))
        stdout = io.BytesIO()
        serve(guard, stdin, stdout)
        stdout.seek(0)
        self.assertEqual(read_message(stdout)["id"], 1)
        self.assertEqual(read_message(stdout)["action"], "send")
        self.assertIsNone(read_message(stdout))


if __name__ == "__main__":
    unittest.main()
