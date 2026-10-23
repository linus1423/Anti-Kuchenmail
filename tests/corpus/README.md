# Test-Korpus

- `cake/`: Kuchenmails, die erkannt werden müssen (N2: mindestens 95 %).
- `normal/`: normale Arbeitsmails, die durchgehen müssen (N3: höchstens 2 Fehlalarme). Darunter bewusst schwierige Fälle: Essen ohne Angebot, Angebot ohne Essen, Antworten und Weiterleitungen von Kuchenmails, Tortendiagramme.

Dateiname: `<Nummer>-<Sprache>.eml`, Sprache `de` oder `en`.

Alle Mails sind ausgedacht und wurden zusammen mit den Regeln geschrieben. Die Trefferquote hier ist deshalb optimistisch. Echte (anonymisierte) Kuchenmails gehören als neue Dateien nach `cake/`; wenn eine nicht erkannt wird, Regeln in `guard/default_rules.toml` nachschärfen.

Prüfen einzelner Mails: `python3 -m guard.classify tests/corpus/cake/*.eml`
