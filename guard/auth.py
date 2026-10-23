"""Freigabe einer verdächtigen Mail per Passwortabfrage (zenity + PAM)."""

import enum
import logging
import shutil
import subprocess

from guard import pam

log = logging.getLogger("kuchenmail_guard")

MAX_ATTEMPTS = 3
DIALOG_TIMEOUT_S = 120
ZENITY_TIMEOUT_EXIT = 5


class Outcome(enum.Enum):
    RELEASED = "released"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AuthUnavailable(RuntimeError):
    pass


def _markup_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ask_password_zenity(subject: str, attempt: int, run=subprocess.run) -> str | None:
    """Zeigt den Passwortdialog. None bei Abbruch oder Zeitüberschreitung."""
    if not shutil.which("zenity"):
        raise AuthUnavailable("zenity ist nicht installiert")
    text = (
        "Diese Mail sieht aus wie eine <b>Kuchenmail</b>.\n\n"
        f"Betreff: {_markup_escape(subject or '(kein Betreff)')}\n\n"
        "Zum Senden das Passwort des Rechners eingeben."
    )
    if attempt > 1:
        text += f"\n\n<b>Falsches Passwort.</b> Versuch {attempt} von {MAX_ATTEMPTS}."
    try:
        result = run(
            ["zenity", "--entry", "--hide-text", "--title", "Kuchenmail-Guard",
             "--text", text, f"--timeout={DIALOG_TIMEOUT_S}"],
            capture_output=True, text=True, timeout=DIALOG_TIMEOUT_S + 10,
        )
    except subprocess.TimeoutExpired:
        return None
    except OSError as exc:
        raise AuthUnavailable(f"zenity konnte nicht gestartet werden: {exc}") from exc
    if result.returncode != 0:
        if result.returncode == ZENITY_TIMEOUT_EXIT:
            log.info("Passwortdialog nach %s s abgelaufen", DIALOG_TIMEOUT_S)
        return None
    return result.stdout.rstrip("\n")


def check_password(password: str) -> bool:
    try:
        return pam.authenticate(password)
    except pam.PamUnavailable as exc:
        raise AuthUnavailable(str(exc)) from exc


def confirm_send(subject: str, ask=ask_password_zenity, check=check_password) -> Outcome:
    """Fragt bis zu MAX_ATTEMPTS-mal nach dem Passwort."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        password = ask(subject, attempt)
        if password is None:
            return Outcome.CANCELLED
        if password and check(password):
            return Outcome.RELEASED
        log.info("Falsches Passwort (Versuch %s von %s)", attempt, MAX_ATTEMPTS)
    return Outcome.FAILED
