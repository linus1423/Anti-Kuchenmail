import unittest
from pathlib import Path

from guard.quotes import html_to_text, strip_quotes

FIXTURES = Path(__file__).parent / "fixtures" / "quotes"
CLIENTS = ("gmail", "thunderbird", "outlook", "roundcube")


class FixtureTest(unittest.TestCase):
    def test_html_quotes_are_removed_for_every_client(self):
        for client in CLIENTS:
            with self.subTest(client=client):
                html = (FIXTURES / f"{client}.html").read_text(encoding="utf-8")
                self.assertEqual(strip_quotes("", html), "Neuer Text von mir.")

    def test_plain_quotes_are_removed_for_every_client(self):
        for client in CLIENTS:
            with self.subTest(client=client):
                text = (FIXTURES / f"{client}.txt").read_text(encoding="utf-8")
                self.assertEqual(strip_quotes(text), "Neuer Text von mir.")


class PlainTextTest(unittest.TestCase):
    def test_text_without_quotes_is_unchanged(self):
        self.assertEqual(strip_quotes("Hallo\n\nIch bringe Kuchen mit."), "Hallo\n\nIch bringe Kuchen mit.")

    def test_quote_lines_in_the_middle_are_dropped(self):
        text = "Oben\n> zitiert\nUnten"
        self.assertEqual(strip_quotes(text), "Oben\nUnten")

    def test_english_reply_header(self):
        text = "Thanks!\n\nOn Wed, Oct 21, 2026 at 3:00 PM Max <max@x.example> wrote:\nI'll bring cake"
        self.assertEqual(strip_quotes(text), "Thanks!")

    def test_forward_header_cuts_rest(self):
        text = "Schau mal\n\n---------- Forwarded message ---------\nKuchen für alle"
        self.assertEqual(strip_quotes(text), "Schau mal")

    def test_von_line_without_header_fields_is_kept(self):
        text = "Von: diesem Text bleibt alles erhalten\nweil keine Kopfzeilen folgen"
        self.assertEqual(strip_quotes(text), text)


class HtmlTest(unittest.TestCase):
    def test_html_preferred_over_plain(self):
        self.assertEqual(strip_quotes("plain", "<p>html</p>"), "html")

    def test_empty_html_falls_back_to_plain(self):
        self.assertEqual(strip_quotes("plain", "   "), "plain")

    def test_block_elements_become_line_breaks(self):
        self.assertEqual(html_to_text("<p>a</p><p>b</p>c<br>d"), "a\n\nb\nc\nd")

    def test_script_and_style_are_ignored(self):
        self.assertEqual(html_to_text("<style>p{}</style><p>x</p><script>y()</script>"), "x")

    def test_unclosed_tags_do_not_swallow_text(self):
        self.assertEqual(html_to_text("<div><blockquote>q</div>danach"), "danach")

    def test_entities_are_decoded(self):
        self.assertEqual(html_to_text("<p>K&uuml;che &amp; Kuchen&nbsp;!</p>"), "Küche & Kuchen !")


if __name__ == "__main__":
    unittest.main()
