"""Lädt die Erkennungsregeln aus TOML, mit Cache und Fallback auf die Standardregeln."""

import logging
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from guard.text import normalize

log = logging.getLogger("kuchenmail_guard")

DEFAULT_RULES_PATH = Path(__file__).with_name("default_rules.toml")

PATTERN_GROUPS = ("food", "strong_offer", "weak_offer", "timing", "distribution")
WEIGHT_KEYS = ("strong_offer", "weak_offer", "timing", "recipients", "food_density")


class RulesError(ValueError):
    pass


@dataclass(frozen=True)
class Rules:
    threshold: float
    recipient_limit: int
    lock_on_detect: bool
    weights: dict[str, float]
    food_density_min: int
    patterns: dict[str, tuple[re.Pattern, ...]]
    source: str


def user_rules_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "kuchenmail-guard" / "rules.toml"


def _read_toml(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _merge(defaults: dict, overrides: dict) -> dict:
    """Unterabschnitte (weights, patterns) werden schlüsselweise überschrieben, alles andere ersetzt."""
    merged = dict(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def _number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RulesError(f"{name} muss eine Zahl sein")
    return float(value)


def _compile(raw: dict, source: str) -> Rules:
    weights = raw.get("weights", {})
    patterns = raw.get("patterns", {})
    if not isinstance(weights, dict) or not isinstance(patterns, dict):
        raise RulesError("[weights] und [patterns] müssen Tabellen sein")

    compiled = {}
    for group in PATTERN_GROUPS:
        items = patterns.get(group, [])
        if not isinstance(items, list) or not all(isinstance(p, str) for p in items):
            raise RulesError(f"patterns.{group} muss eine Liste von Texten sein")
        try:
            compiled[group] = tuple(re.compile(normalize(p)) for p in items)
        except re.error as exc:
            raise RulesError(f"patterns.{group}: ungültiges Muster ({exc})") from exc

    lock_on_detect = raw.get("lock_on_detect", False)
    if not isinstance(lock_on_detect, bool):
        raise RulesError("lock_on_detect muss true oder false sein")

    return Rules(
        threshold=_number(raw.get("threshold"), "threshold"),
        recipient_limit=int(_number(raw.get("recipient_limit"), "recipient_limit")),
        lock_on_detect=lock_on_detect,
        weights={k: _number(weights.get(k, 0), f"weights.{k}") for k in WEIGHT_KEYS},
        food_density_min=int(_number(weights.get("food_density_min", 3), "weights.food_density_min")),
        patterns=compiled,
        source=source,
    )


_defaults_cache: tuple[dict, Rules] | None = None
_user_cache: dict[Path, tuple[int, Rules]] = {}
_missing_logged: set[Path] = set()


def _defaults() -> tuple[dict, Rules]:
    global _defaults_cache
    if _defaults_cache is None:
        raw = _read_toml(DEFAULT_RULES_PATH)
        _defaults_cache = (raw, _compile(raw, "default"))
    return _defaults_cache


def load_rules(path: Path | None = None) -> Rules:
    """Liefert die aktuellen Regeln.

    Die Datei wird nur neu gelesen, wenn sich ihre Änderungszeit geändert hat. Fehlt sie
    oder ist sie fehlerhaft, gelten die Standardregeln und es wird eine Warnung geloggt.
    """
    path = path or user_rules_path()
    default_raw, default_rules = _defaults()

    try:
        mtime = path.stat().st_mtime_ns
    except FileNotFoundError:
        _user_cache.pop(path, None)
        if path not in _missing_logged:
            log.warning("Keine Regeldatei unter %s, nutze Standardregeln", path)
            _missing_logged.add(path)
        return default_rules

    cached = _user_cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        rules = _compile(_merge(default_raw, _read_toml(path)), str(path))
    except (tomllib.TOMLDecodeError, RulesError, OSError) as exc:
        log.warning("Regeldatei %s fehlerhaft (%s), nutze Standardregeln", path, exc)
        rules = default_rules
    _user_cache[path] = (mtime, rules)
    _missing_logged.discard(path)
    return rules

