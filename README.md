# Anti-Kuchenmail

Lokales Tool für Fedora, das Kuchenmails erkennt, bevor sie rausgehen. Wer an einem entsperrten Rechner schnell „Ich bringe morgen Kuchen mit“ verschicken will, bekommt eine Passwortabfrage statt eines gesendeten Streichs.

Abgedeckt werden Thunderbird sowie Gmail, Outlook im Web und Roundcube in Firefox. Alles läuft lokal, ohne Netzwerkverbindungen.

## Stand

In Entwicklung. Planung und Fortschritt stehen in [`specs/kuchenmail-guard/`](specs/kuchenmail-guard/) (Anforderungen, Design, Tasks).

## Entwicklung

Voraussetzung: Python 3.11 oder neuer (auf Fedora vorinstalliert), keine weiteren Pakete.

```sh
make test   # Tests
make lint   # Syntax-Check
```
