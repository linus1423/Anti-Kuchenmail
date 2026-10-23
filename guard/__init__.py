"""Kuchenmail-Guard: erkennt Kuchenmails lokal und hält den Versand an."""

import sys

__version__ = "0.1.0"

MIN_PYTHON = (3, 11)  # tomllib

if sys.version_info < MIN_PYTHON:
    raise RuntimeError(
        f"Kuchenmail-Guard braucht Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} oder neuer"
    )
