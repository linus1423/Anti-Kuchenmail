"""Native-Messaging-Host für die Thunderbird- und die Webmail-Erweiterung.

Protokoll (WebExtensions): je Nachricht 4 Byte Länge in nativer Byte-Reihenfolge,
danach UTF-8-JSON. Der Host läuft, solange die Erweiterung den Port offen hält.

Anfragen:
  {"type": "ping"}  → {"ok", "version", "lock_on_detect"}
  {"type": "before_send", "client", "subject", "plain_text", "html", "recipients", ["id"]}
  {"type": "check", ... wie before_send ..., "draft_id"}
Antworten tragen die "id" der Anfrage, falls vorhanden.
"""

import json
import logging
import struct
import sys
from typing import BinaryIO

from guard import __version__, auth
from guard.attempt_log import Attempt, AttemptLog
from guard.classifier import classify
from guard.lock import lock_screen
from guard.model import MailDraft
from guard.rules import load_rules

log = logging.getLogger("kuchenmail_guard")

MAX_MESSAGE_BYTES = 4 * 1024 * 1024
CLIENTS = ("thunderbird", "gmail", "outlook", "roundcube")


class ProtocolError(ValueError):
    pass


def read_message(stream: BinaryIO) -> dict | None:
    header = stream.read(4)
    if not header:
        return None
    if len(header) < 4:
        raise ProtocolError("unvollständiger Längenkopf")
    (length,) = struct.unpack("=I", header)
    if length > MAX_MESSAGE_BYTES:
        raise ProtocolError(f"Nachricht zu groß ({length} Bytes)")
    payload = stream.read(length)
    if len(payload) < length:
        raise ProtocolError("unvollständige Nachricht")
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"kein gültiges JSON: {exc}") from exc
    if not isinstance(message, dict):
        raise ProtocolError("Nachricht ist kein Objekt")
    return message


def write_message(stream: BinaryIO, message: dict) -> None:
    payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
    stream.write(struct.pack("=I", len(payload)) + payload)
    stream.flush()


def draft_from_message(message: dict) -> MailDraft:
    def text(key, default=""):
        value = message.get(key, default)
        if value is None:
            return default
        if not isinstance(value, str):
            raise ProtocolError(f"{key} muss Text sein")
        return value

    recipients = message.get("recipients", [])
    if not isinstance(recipients, list) or not all(isinstance(r, str) for r in recipients):
        raise ProtocolError("recipients muss eine Liste von Texten sein")
    client = text("client")
    if client not in CLIENTS:
        raise ProtocolError(f"unbekannter client: {client!r}")
    return MailDraft(
        client=client,
        subject=text("subject"),
        plain_text=text("plain_text"),
        html=text("html", None),
        recipients=tuple(recipients),
    )


class Guard:
    def __init__(self, rules_loader=load_rules, attempt_log=None, confirm=auth.confirm_send, lock=lock_screen):
        self.rules_loader = rules_loader
        self.attempt_log = attempt_log or AttemptLog()
        self.confirm = confirm
        self.lock = lock
        self.locked_drafts: set[str] = set()

    def handle(self, message: dict) -> dict:
        kind = message.get("type")
        try:
            if kind == "ping":
                rules = self.rules_loader()
                response = {"ok": True, "version": __version__, "lock_on_detect": rules.lock_on_detect}
            elif kind == "before_send":
                response = self.before_send(draft_from_message(message))
            elif kind == "check":
                response = self.check(draft_from_message(message), str(message.get("draft_id", "")))
            else:
                response = {"error": "unknown_type"}
        except ProtocolError as exc:
            log.warning("Ungültige Nachricht: %s", exc)
            response = {"error": "invalid_message", "detail": str(exc)}
        if "id" in message:
            response["id"] = message["id"]
        return response

    def _record(self, draft, verdict, outcome):
        try:
            self.attempt_log.append(Attempt.new(draft, verdict, outcome))
        except OSError as exc:
            log.error("Versuch konnte nicht protokolliert werden: %s", exc)

    def before_send(self, draft: MailDraft) -> dict:
        verdict = classify(draft, self.rules_loader())
        if not verdict.suspicious:
            return {"action": "send", "suspicious": False, "score": verdict.score}

        log.info("Kuchenmail-Verdacht (%s, Score %.2f): %s", draft.client, verdict.score, ", ".join(verdict.hits))
        try:
            outcome = self.confirm(draft.subject)
        except auth.AuthUnavailable as exc:
            log.error("Passwortabfrage nicht möglich: %s", exc)
            self._record(draft, verdict, "cancelled")
            return {"action": "cancel", "suspicious": True, "score": verdict.score, "reason": "auth_unavailable"}

        base = {"suspicious": True, "score": verdict.score}
        if outcome is auth.Outcome.RELEASED:
            self._record(draft, verdict, "released")
            return {"action": "send", **base}
        if outcome is auth.Outcome.CANCELLED:
            self._record(draft, verdict, "cancelled")
            return {"action": "cancel", **base}
        self._record(draft, verdict, "locked")
        self.lock()
        return {"action": "discard", **base}

    def check(self, draft: MailDraft, draft_id: str) -> dict:
        rules = self.rules_loader()
        verdict = classify(draft, rules)
        locked = False
        if verdict.suspicious and rules.lock_on_detect and draft_id not in self.locked_drafts:
            # Pro Entwurf nur einmal sperren, sonst sperrt es nach dem Entsperren sofort wieder
            self.locked_drafts.add(draft_id)
            self._record(draft, verdict, "locked_on_detect")
            locked = self.lock()
        return {"suspicious": verdict.suspicious, "score": verdict.score, "locked": locked}


def serve(guard: Guard, stdin: BinaryIO, stdout: BinaryIO) -> None:
    while True:
        try:
            message = read_message(stdin)
        except ProtocolError as exc:
            log.error("Protokollfehler, beende: %s", exc)
            write_message(stdout, {"error": "protocol", "detail": str(exc)})
            return
        if message is None:
            return
        write_message(stdout, guard.handle(message))


def main() -> None:
    from guard.logsetup import setup_logging

    setup_logging("host")
    log.info("Host gestartet (Version %s)", __version__)
    serve(Guard(), sys.stdin.buffer, sys.stdout.buffer)
    log.info("Host beendet")


if __name__ == "__main__":
    main()
