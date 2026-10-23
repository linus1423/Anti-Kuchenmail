import time
import unittest

from guard.classifier import classify
from guard.model import MailDraft
from tests.helpers import default_rules

ONE = ("anna@firma.example",)
MANY = tuple(f"p{i}@firma.example" for i in range(5))


def draft(text="", subject="", recipients=ONE, html=None):
    return MailDraft(client="test", subject=subject, plain_text=text, html=html, recipients=recipients)


class ClassifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = default_rules()

    def check(self, d):
        return classify(d, self.rules)

    def test_classic_cake_mail_is_suspicious(self):
        verdict = self.check(draft("Ich bringe morgen Kuchen mit."))
        self.assertTrue(verdict.suspicious)
        self.assertIn("food:kuchen", verdict.hits)

    def test_cake_in_subject_and_offer_in_body(self):
        self.assertTrue(self.check(draft("Bring ich morgen mit!", subject="Kuchen")).suspicious)

    def test_food_and_offer_in_neighbouring_sentences(self):
        self.assertTrue(self.check(draft("Wer will Mettbrötchen? Ich bring welche mit!")).suspicious)

    def test_food_and_offer_far_apart_do_not_count(self):
        text = "Ich bringe die Unterlagen mit. Zweiter Satz. Dritter Satz. In der Küche steht Kuchen."
        self.assertFalse(self.check(draft(text)).suspicious)

    def test_food_without_offer_is_not_suspicious(self):
        self.assertFalse(self.check(draft("In der Küche steht noch Kuchen.", recipients=MANY)).suspicious)

    def test_offer_without_food_is_not_suspicious(self):
        self.assertFalse(self.check(draft("Ich bringe morgen die Unterlagen mit.", recipients=MANY)).suspicious)

    def test_english_is_detected(self):
        self.assertTrue(self.check(draft("I'll bring donuts tomorrow!")).suspicious)

    def test_umlauts_and_case_are_normalized(self):
        self.assertTrue(self.check(draft("MORGEN BRINGE ICH BRÖTCHEN MIT")).suspicious)

    def test_weak_offer_needs_more_signals(self):
        weak = draft("Kuchen für euch in der Küche.")
        self.assertFalse(self.check(weak).suspicious)
        stronger = draft("Morgen Kuchen für euch in der Küche.", recipients=MANY)
        self.assertTrue(self.check(stronger).suspicious)

    def test_many_recipients_add_to_score(self):
        few = self.check(draft("Kuchen für euch.", recipients=ONE))
        many = self.check(draft("Kuchen für euch.", recipients=MANY))
        self.assertAlmostEqual(many.score - few.score, self.rules.weights["recipients"])
        self.assertIn("recipients>3", many.hits)

    def test_exactly_recipient_limit_is_not_many(self):
        verdict = self.check(draft("Hallo", recipients=MANY[:3]))
        self.assertNotIn("recipients>3", verdict.hits)

    def test_distribution_address_adds_to_score(self):
        verdict = self.check(draft("Kuchen für euch.", recipients=("team@firma.example",)))
        self.assertIn("recipients:distribution", verdict.hits)

    def test_poem_with_many_food_words(self):
        poem = "Oh Kuchen, du mein Glück,\nfür euch ein Stück.\nTorte, Muffins, Schokolade,\nwär doch schade."
        self.assertTrue(self.check(draft(poem)).suspicious)

    def test_quoted_cake_mail_is_ignored(self):
        text = "Danke, freue mich!\n\nAm 21.10.2026 um 10:00 schrieb Max:\n> Ich bringe morgen Kuchen mit."
        self.assertFalse(self.check(draft(text, recipients=MANY)).suspicious)

    def test_html_body_is_used(self):
        verdict = self.check(draft("", html="<p>Morgen bringe ich <b>Muffins</b> mit!</p>"))
        self.assertTrue(verdict.suspicious)

    def test_empty_mail(self):
        verdict = self.check(draft(""))
        self.assertFalse(verdict.suspicious)
        self.assertEqual(verdict.score, 0)

    def test_ten_kilobytes_under_200_ms(self):
        text = ("Dies ist ein ganz normaler Satz über das Projekt und den Zeitplan. " * 160)[:10_000]
        text += "\nIch bringe morgen Kuchen mit."
        start = time.perf_counter()
        verdict = self.check(draft(text, recipients=MANY))
        elapsed = time.perf_counter() - start
        self.assertTrue(verdict.suspicious)
        self.assertLess(elapsed, 0.2)


if __name__ == "__main__":
    unittest.main()
