"""Bildschirm sperren (GNOME)."""

import logging
import subprocess

log = logging.getLogger("kuchenmail_guard")

COMMANDS = (
    ["loginctl", "lock-session"],
    [
        "gdbus", "call", "--session",
        "--dest", "org.gnome.ScreenSaver",
        "--object-path", "/org/gnome/ScreenSaver",
        "--method", "org.gnome.ScreenSaver.Lock",
    ],
)


def lock_screen(run=subprocess.run) -> bool:
    """Sperrt die Sitzung. Liefert False, wenn keiner der Wege funktioniert hat."""
    for command in COMMANDS:
        try:
            result = run(command, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError) as exc:
            log.warning("Sperren mit %s fehlgeschlagen: %s", command[0], exc)
            continue
        if result.returncode == 0:
            return True
        log.warning("Sperren mit %s fehlgeschlagen (Exit %s): %s", command[0], result.returncode, result.stderr.strip())
    log.error("Bildschirm konnte nicht gesperrt werden")
    return False
