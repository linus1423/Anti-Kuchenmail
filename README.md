# Anti-Kuchenmail

Wer an einem entsperrten Rechner schnell „Ich bringe morgen Kuchen mit“ an das ganze Team schicken will, bekommt stattdessen eine Passwortabfrage. Kuchenmail-Guard erkennt solche Mails beim Senden in **Thunderbird**, **Gmail**, **Outlook im Web** und **Roundcube** (in Firefox) und lässt sie nur mit dem Passwort des Rechners raus. Nach drei falschen Versuchen wird der Entwurf verworfen und der Bildschirm gesperrt. Beim nächsten Entsperren erfährst du, wer es wann versucht hat.

Alles läuft lokal auf Fedora: keine Netzwerkverbindungen, keine Telemetrie, kein Root.

## Installation

Voraussetzungen: Fedora mit GNOME, Python 3.11+ (vorinstalliert), `zenity` (in Fedora Workstation enthalten), Thunderbird und Firefox als dnf-Pakete.

```sh
git clone https://github.com/linus1423/Anti-Kuchenmail.git
cd Anti-Kuchenmail
./install.sh
```

Danach einmalig:

1. **Thunderbird:** Add-ons und Themes → Zahnrad → „Add-on aus Datei installieren“ → `~/.local/share/kuchenmail-guard/kuchenmail-guard-thunderbird.xpi`
2. **Firefox:** Die Erweiterung muss einmal bei Mozilla signiert werden (siehe „Firefox-Erweiterung signieren“). Dann Datei → Datei öffnen → `~/.local/share/kuchenmail-guard/kuchenmail-guard-webmail.xpi`
3. **Roundcube:** In Firefox unter Add-ons → Kuchenmail-Guard (Webmail) → Einstellungen die Adresse jeder Roundcube-Instanz eintragen, z. B. `https://webmail.example.de`

## Regeln anpassen

`~/.config/kuchenmail-guard/rules.toml` enthält nur deine Abweichungen von den Standardregeln (`guard/default_rules.toml`, dort ist alles erklärt). Änderungen gelten sofort.

Nützlich:

```toml
lock_on_detect = true    # schon beim Schreiben sperren
threshold = 1.2          # weniger empfindlich
```

Ob eine Mail erkannt würde, prüfst du so: `python3 -m guard.classify mail.eml`

## Wenn das Tool kaputt ist

Ohne laufenden Guard wird **nicht gesendet** (fail-closed), du siehst dann den Hinweis „Kuchenmail-Guard nicht erreichbar“. Zum Senden ohne Schutz die Erweiterung in Thunderbird bzw. Firefox kurz deaktivieren. Fehler stehen in `~/.local/state/kuchenmail-guard/guard.log`.

## Deinstallation

```sh
./uninstall.sh
```

Danach die Erweiterungen in Thunderbird und Firefox entfernen. Eigene Regeln und das Protokoll bleiben erhalten (Pfade nennt das Skript).

## Grenzen

Das hält Gelegenheits-Streiche auf, keine gezielten Angriffe: Wer am entsperrten Rechner sitzt, kann die Erweiterung auch deaktivieren. Mails vom Handy oder aus anderen Browsern werden nicht erfasst.

## Entwicklung

Planung, Design und Fortschritt: [`specs/kuchenmail-guard/`](specs/kuchenmail-guard/). Abnahme-Checkliste: [`docs/e2e-checklist.md`](docs/e2e-checklist.md).

```sh
make test       # Python-Tests (nur Standardbibliothek)
npm install     # einmalig, für JS-Tests, Lint und Signieren
make check      # Lint + Python- + JS-Tests
```

### Firefox-Erweiterung signieren

Auf addons.mozilla.org anmelden → Werkzeuge → API-Schlüssel verwalten. Dann:

```sh
AMO_JWT_ISSUER=… AMO_JWT_SECRET=… make sign-webmail
./install.sh
```

Hochgeladen wird nur der Code der Erweiterung, keine Mails. Die signierte Datei landet in `dist/` und wird vom Installer übernommen.
