"""Bewertet, ob eine Mail eine Kuchenmail ist (gewichtete Regeln, siehe default_rules.toml)."""

import re

from guard.model import MailDraft, Verdict
from guard.quotes import strip_quotes
from guard.rules import Rules
from guard.text import normalize

_UNIT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _units(subject: str, body: str) -> list[str]:
    units = [subject] if subject.strip() else []
    units += [u for u in _UNIT_SPLIT.split(body) if u.strip()]
    return units


def _windows(units: list[str]) -> list[str]:
    """Jeder Satz zusammen mit seinem Nachfolger, damit 'Kuchen? Bring ich mit!' zählt."""
    if len(units) < 2:
        return units
    return [f"{a} {b}" for a, b in zip(units, units[1:])]


def _first_match(patterns, text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    return None


def _is_distribution(address: str, rules: Rules) -> bool:
    address = normalize(address.strip())
    return any(p.search(address) for p in rules.patterns["distribution"])


def classify(draft: MailDraft, rules: Rules) -> Verdict:
    body = normalize(strip_quotes(draft.plain_text, draft.html))
    subject = normalize(draft.subject)
    units = _units(subject, body)
    windows = _windows(units)
    p = rules.patterns
    w = rules.weights

    hits: list[str] = []
    score = 0.0

    offer_found = None  # (Gewicht, Treffer)
    timing_hit = None
    for window in windows:
        food = _first_match(p["food"], window)
        if not food:
            continue
        strong = _first_match(p["strong_offer"], window)
        if strong and (offer_found is None or offer_found[0] < w["strong_offer"]):
            offer_found = (w["strong_offer"], f"food:{food}", f"offer:{strong}")
        weak = _first_match(p["weak_offer"], window)
        if weak and offer_found is None:
            offer_found = (w["weak_offer"], f"food:{food}", f"weak_offer:{weak}")
        timing_hit = timing_hit or _first_match(p["timing"], window)

    if offer_found:
        score += offer_found[0]
        hits += offer_found[1:]
    if timing_hit:
        score += w["timing"]
        hits.append(f"timing:{timing_hit}")

    full_text = f"{subject}\n{body}"
    food_count = sum(len(pattern.findall(full_text)) for pattern in p["food"])
    if food_count >= rules.food_density_min:
        score += w["food_density"]
        hits.append(f"food_density:{food_count}")

    recipients = [r for r in draft.recipients if r.strip()]
    if len(recipients) > rules.recipient_limit:
        score += w["recipients"]
        hits.append(f"recipients>{rules.recipient_limit}")
    elif any(_is_distribution(r, rules) for r in recipients):
        score += w["recipients"]
        hits.append("recipients:distribution")

    score = round(score, 3)
    return Verdict(suspicious=score >= rules.threshold, score=score, hits=tuple(hits))
