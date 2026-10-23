from pathlib import Path

from guard.rules import DEFAULT_RULES_PATH, load_rules

CORPUS = Path(__file__).parent / "corpus"


def default_rules():
    """Standardregeln, unabhängig von einer Regeldatei im Home-Verzeichnis."""
    return load_rules(DEFAULT_RULES_PATH)
