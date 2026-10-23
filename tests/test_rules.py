import os
import tempfile
import unittest
from pathlib import Path

from guard import rules as rules_module
from guard.rules import load_rules, user_rules_path


class RulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "rules.toml"
        rules_module._user_cache.clear()
        rules_module._missing_logged.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, content: str, mtime_ns: int):
        self.path.write_text(content, encoding="utf-8")
        os.utime(self.path, ns=(mtime_ns, mtime_ns))

    def test_defaults_load_and_compile(self):
        with self.assertLogs("kuchenmail_guard", "WARNING"):
            rules = load_rules(self.path)
        self.assertEqual(rules.source, "default")
        self.assertEqual(rules.threshold, 1.0)
        self.assertEqual(rules.recipient_limit, 3)
        self.assertFalse(rules.lock_on_detect)
        for group in rules_module.PATTERN_GROUPS:
            self.assertTrue(rules.patterns[group], group)

    def test_missing_file_warns_only_once(self):
        with self.assertLogs("kuchenmail_guard", "WARNING") as logs:
            load_rules(self.path)
            load_rules(self.path)
        self.assertEqual(len(logs.records), 1)

    def test_user_file_overrides_single_values(self):
        self.write("threshold = 2.5\n[weights]\ntiming = 0.9\n", 1_000_000_000)
        rules = load_rules(self.path)
        self.assertEqual(rules.threshold, 2.5)
        self.assertEqual(rules.weights["timing"], 0.9)
        self.assertEqual(rules.weights["strong_offer"], 1.0)  # aus den Standardregeln
        self.assertTrue(rules.patterns["food"])

    def test_pattern_list_replaces_default_list_and_is_normalized(self):
        self.write('[patterns]\nfood = ["Käsekuchen"]\n', 1_000_000_000)
        rules = load_rules(self.path)
        self.assertEqual([p.pattern for p in rules.patterns["food"]], ["kaesekuchen"])

    def test_changes_are_picked_up_without_restart(self):
        self.write("threshold = 2.0\n", 1_000_000_000)
        self.assertEqual(load_rules(self.path).threshold, 2.0)
        self.write("threshold = 3.0\n", 2_000_000_000)
        self.assertEqual(load_rules(self.path).threshold, 3.0)

    def test_unchanged_file_is_served_from_cache(self):
        self.write("threshold = 2.0\n", 1_000_000_000)
        first = load_rules(self.path)
        self.assertIs(load_rules(self.path), first)

    def test_broken_toml_falls_back_with_warning(self):
        self.write("threshold = = 1\n", 1_000_000_000)
        with self.assertLogs("kuchenmail_guard", "WARNING") as logs:
            rules = load_rules(self.path)
        self.assertEqual(rules.source, "default")
        self.assertIn("fehlerhaft", logs.output[0])

    def test_invalid_regex_falls_back(self):
        self.write('[patterns]\nfood = ["(kuchen"]\n', 1_000_000_000)
        with self.assertLogs("kuchenmail_guard", "WARNING"):
            self.assertEqual(load_rules(self.path).source, "default")

    def test_wrong_types_fall_back(self):
        for content in ('threshold = "hoch"\n', "lock_on_detect = 1\n", "[patterns]\nfood = [1, 2]\n"):
            with self.subTest(content=content):
                rules_module._user_cache.clear()
                self.write(content, 1_000_000_000)
                with self.assertLogs("kuchenmail_guard", "WARNING"):
                    self.assertEqual(load_rules(self.path).source, "default")

    def test_user_rules_path_respects_xdg(self):
        old = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = "/tmp/xdg-test"
        try:
            self.assertEqual(user_rules_path(), Path("/tmp/xdg-test/kuchenmail-guard/rules.toml"))
        finally:
            if old is None:
                del os.environ["XDG_CONFIG_HOME"]
            else:
                os.environ["XDG_CONFIG_HOME"] = old


if __name__ == "__main__":
    unittest.main()
