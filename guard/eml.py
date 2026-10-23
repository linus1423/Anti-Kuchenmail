"""Liest .eml-Dateien als MailDraft ein (für die Kommandozeile und das Test-Korpus)."""

from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from pathlib import Path

from guard.model import MailDraft


def draft_from_eml(path: Path, client: str = "eml") -> MailDraft:
    with Path(path).open("rb") as fh:
        message = BytesParser(policy=policy.default).parse(fh)

    plain = message.get_body(preferencelist=("plain",))
    html = message.get_body(preferencelist=("html",))
    headers = [str(v) for key in ("to", "cc", "bcc") for v in message.get_all(key, [])]
    recipients = tuple(addr for _, addr in getaddresses(headers) if addr)

    return MailDraft(
        client=client,
        subject=str(message.get("subject", "")),
        plain_text=plain.get_content() if plain else "",
        html=html.get_content() if html else None,
        recipients=recipients,
    )
