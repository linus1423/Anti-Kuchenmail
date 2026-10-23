"""Vereinheitlichung von Text und Mustern vor dem Vergleich."""

import unicodedata

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue"})
_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'"})


def normalize(text: str) -> str:
    """Kleinschreibung, ß→ss, Umlaute ausgeschrieben, typografische Apostrophe vereinheitlicht."""
    text = unicodedata.normalize("NFC", text).casefold()
    return text.translate(_UMLAUTS).translate(_APOSTROPHES)
