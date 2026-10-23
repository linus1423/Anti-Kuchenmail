"""Meldet abgefangene Kuchenmail-Versuche, sobald der Besitzer wieder da ist.

Läuft als systemd-User-Dienst. Beim Start (= nach der Anmeldung) und bei jedem
Entsperren (D-Bus-Signal org.gnome.ScreenSaver.ActiveChanged(false)) werden alle noch
nicht gemeldeten Versuche per notify-send angezeigt.
"""

import logging
import subprocess
import time
from datetime import datetime

from guard.attempt_log import Attempt, AttemptLog

log = logging.getLogger("kuchenmail_guard")

MONITOR = [
    "gdbus", "monitor", "--session",
    "--dest", "org.gnome.ScreenSaver",
    "--object-path", "/org/gnome/ScreenSaver",
]
UNLOCK_SIGNAL = "org.gnome.ScreenSaver.ActiveChanged (false,)"
MAX_SINGLE_NOTIFICATIONS = 3
RESTART_DELAY_S = 5

OUTCOME_TEXT = {
    "cancelled": "abgebrochen",
    "locked": "3× falsches Passwort, Bildschirm gesperrt",
    "locked_on_detect": "beim Schreiben erkannt, Bildschirm gesperrt",
}
CLIENT_TEXT = {"thunderbird": "Thunderbird", "gmail": "Gmail", "outlook": "Outlook", "roundcube": "Roundcube"}


def _time(attempt: Attempt) -> str:
    try:
        return datetime.fromisoformat(attempt.ts).strftime("%d.%m. %H:%M")
    except ValueError:
        return attempt.ts


def describe(attempt: Attempt) -> str:
    recipients = ", ".join(attempt.recipients[:2]) + (" …" if len(attempt.recipients) > 2 else "")
    parts = [
        f"{_time(attempt)} in {CLIENT_TEXT.get(attempt.client, attempt.client)}",
        f"„{attempt.subject or '(kein Betreff)'}“" + (f" an {recipients}" if recipients else ""),
        OUTCOME_TEXT.get(attempt.outcome, attempt.outcome),
    ]
    return "\n".join(parts)


def notify_send(title: str, body: str, run=subprocess.run) -> None:
    try:
        run(["notify-send", "--app-name=Kuchenmail-Guard", "--icon=dialog-warning", title, body],
            capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        log.error("Benachrichtigung fehlgeschlagen: %s", exc)


def notify_pending(attempt_log: AttemptLog, send=notify_send) -> int:
    """Zeigt offene Versuche an und markiert sie als gemeldet. Liefert die Anzahl Meldungen."""
    pending = attempt_log.pending()
    if not pending:
        return 0
    # Selbst freigegebene Mails kennt der Besitzer schon
    relevant = [a for a in pending if a.outcome != "released"]
    if len(relevant) > MAX_SINGLE_NOTIFICATIONS:
        lines = [describe(a).replace("\n", " · ") for a in relevant[-MAX_SINGLE_NOTIFICATIONS:]]
        send(f"{len(relevant)} Kuchenmails abgefangen", "Zuletzt:\n" + "\n".join(lines))
        count = 1
    else:
        for attempt in relevant:
            send("Kuchenmail abgefangen", describe(attempt))
        count = len(relevant)
    attempt_log.mark_notified([a.id for a in pending])
    return count


def watch_unlocks(lines, on_unlock) -> None:
    for line in lines:
        if UNLOCK_SIGNAL in line:
            on_unlock()


def run_forever(attempt_log: AttemptLog, send=notify_send, popen=subprocess.Popen, sleep=time.sleep, rounds=None) -> None:
    notify_pending(attempt_log, send)
    done = 0
    while rounds is None or done < rounds:
        done += 1
        try:
            with popen(MONITOR, stdout=subprocess.PIPE, text=True) as monitor:
                watch_unlocks(monitor.stdout, lambda: notify_pending(attempt_log, send))
        except OSError as exc:
            log.error("gdbus monitor nicht startbar: %s", exc)
        sleep(RESTART_DELAY_S)


def main() -> None:
    from guard.logsetup import setup_logging

    setup_logging("notifier")
    log.info("Notifier gestartet")
    run_forever(AttemptLog())


if __name__ == "__main__":
    main()
