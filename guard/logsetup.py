"""Logging in ~/.local/state/kuchenmail-guard/guard.log (nur für den Nutzer lesbar)."""

import logging
import os
from logging.handlers import RotatingFileHandler

from guard.paths import ensure_private_dir, state_dir


def setup_logging(name: str) -> logging.Logger:
    logger = logging.getLogger("kuchenmail_guard")
    if logger.handlers:
        return logger
    path = ensure_private_dir(state_dir()) / "guard.log"
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    os.close(fd)
    path.chmod(0o600)
    handler = RotatingFileHandler(path, maxBytes=256_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter(f"%(asctime)s {name} %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
