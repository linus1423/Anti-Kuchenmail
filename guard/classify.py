"""Kommandozeile: prüft .eml-Dateien auf Kuchenmail-Verdacht.

    python3 -m guard.classify mail.eml [weitere.eml ...] [--rules regeln.toml]

Exit-Code 0: alle unauffällig, 1: mindestens ein Verdacht, 2: Fehler.
"""

import argparse
import sys
from pathlib import Path

from guard.classifier import classify
from guard.eml import draft_from_eml
from guard.rules import load_rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m guard.classify", description="Kuchenmail-Check für .eml-Dateien")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--rules", type=Path, help="Regeldatei (Standard: ~/.config/kuchenmail-guard/rules.toml)")
    args = parser.parse_args(argv)

    rules = load_rules(args.rules)
    any_suspicious = False
    for path in args.files:
        try:
            verdict = classify(draft_from_eml(path), rules)
        except OSError as exc:
            print(f"{path}: Fehler: {exc}", file=sys.stderr)
            return 2
        label = "KUCHENMAIL-VERDACHT" if verdict.suspicious else "unauffällig"
        print(f"{path}: {label} (Score {verdict.score:.2f}) {', '.join(verdict.hits)}")
        any_suspicious |= verdict.suspicious
    return 1 if any_suspicious else 0


if __name__ == "__main__":
    sys.exit(main())
