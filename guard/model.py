"""Datentypen, die zwischen Erweiterungen, Host und Klassifikator ausgetauscht werden."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MailDraft:
    """Eine Mail, wie sie beim Senden aus dem Mail-Client kommt. Lebt nur im Speicher."""

    client: str
    subject: str = ""
    plain_text: str = ""
    html: str | None = None
    recipients: tuple[str, ...] = ()


@dataclass(frozen=True)
class Verdict:
    suspicious: bool
    score: float
    hits: tuple[str, ...] = field(default_factory=tuple)
