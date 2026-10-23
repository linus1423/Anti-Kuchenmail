"""Treffsicherheit am Test-Korpus (N2: ≥ 95 % erkannt, N3: ≤ 2 Fehlalarme)."""

import unittest

from guard.classifier import classify
from guard.eml import draft_from_eml
from tests.helpers import CORPUS, default_rules


class CorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = default_rules()
        cls.cake = sorted((CORPUS / "cake").glob("*.eml"))
        cls.normal = sorted((CORPUS / "normal").glob("*.eml"))

    def verdicts(self, files):
        return {f.name: classify(draft_from_eml(f), self.rules) for f in files}

    def test_corpus_size(self):
        self.assertGreaterEqual(len(self.cake), 30)
        self.assertGreaterEqual(len(self.normal), 50)
        for kind, files in (("cake", self.cake), ("normal", self.normal)):
            languages = {f.stem.split("-")[1] for f in files}
            self.assertEqual(languages, {"de", "en"}, kind)

    def test_detection_rate_at_least_95_percent(self):
        missed = [name for name, v in self.verdicts(self.cake).items() if not v.suspicious]
        rate = 1 - len(missed) / len(self.cake)
        self.assertGreaterEqual(rate, 0.95, f"Nicht erkannt: {missed}")

    def test_at_most_two_false_alarms(self):
        false_alarms = [f"{name} {v.hits}" for name, v in self.verdicts(self.normal).items() if v.suspicious]
        self.assertLessEqual(len(false_alarms), 2, f"Fehlalarme: {false_alarms}")


if __name__ == "__main__":
    unittest.main()
