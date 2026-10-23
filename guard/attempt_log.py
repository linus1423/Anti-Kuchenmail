"""Protokoll abgefangener Versuche.

Zwei Dateien, beide nur anhängend, damit Host und Benachrichtigungsdienst sich nicht
gegenseitig Einträge überschreiben:

- attempts.jsonl: ein Versuch pro Zeile (ohne Mailtext)
- notified.ids:   IDs der Versuche, die schon gemeldet wurden
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from guard.model import MailDraft, Verdict
from guard.paths import ensure_private_dir, state_dir

OUTCOMES = ("cancelled", "released", "locked", "locked_on_detect")


@dataclass(frozen=True)
class Attempt:
    id: str
    ts: str
    client: str
    subject: str
    recipients: tuple[str, ...]
    score: float
    outcome: str

    @classmethod
    def new(cls, draft: MailDraft, verdict: Verdict, outcome: str) -> "Attempt":
        if outcome not in OUTCOMES:
            raise ValueError(f"unbekannter Ausgang: {outcome}")
        return cls(
            id=str(uuid.uuid4()),
            ts=datetime.now().astimezone().isoformat(timespec="seconds"),
            client=draft.client,
            subject=draft.subject,
            recipients=tuple(draft.recipients),
            score=verdict.score,
            outcome=outcome,
        )


def _append_line(path: Path, line: str) -> None:
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    path.chmod(0o600)


class AttemptLog:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or state_dir()
        self.attempts_path = self.directory / "attempts.jsonl"
        self.notified_path = self.directory / "notified.ids"

    def append(self, attempt: Attempt) -> None:
        ensure_private_dir(self.directory)
        _append_line(self.attempts_path, json.dumps(asdict(attempt), ensure_ascii=False))

    def all(self) -> list[Attempt]:
        try:
            lines = self.attempts_path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        attempts = []
        for line in lines:
            try:
                data = json.loads(line)
                data["recipients"] = tuple(data.get("recipients", ()))
                attempts.append(Attempt(**data))
            except (ValueError, TypeError):
                continue  # halb geschriebene oder fremde Zeile überspringen
        return attempts

    def _notified_ids(self) -> set[str]:
        try:
            return set(self.notified_path.read_text(encoding="utf-8").split())
        except FileNotFoundError:
            return set()

    def pending(self) -> list[Attempt]:
        done = self._notified_ids()
        return [a for a in self.all() if a.id not in done]

    def mark_notified(self, ids) -> None:
        ids = [i for i in ids if i]
        if not ids:
            return
        ensure_private_dir(self.directory)
        _append_line(self.notified_path, "\n".join(ids))
