# Abnahme auf Fedora (T20)

Einmal komplett durchgehen, nachdem alles installiert ist. Empfänger der Testmails: du selbst. Ergebnis (✓/✗ und Auffälligkeiten) in `specs/kuchenmail-guard/tasks.md` unter „Umsetzungsnotizen“ eintragen.

Testtext Kuchenmail: Betreff `Kuchen`, Text „Ich bringe morgen Kuchen mit.“
Testtext normal: Betreff `Test`, Text „Kurzer Test, bitte ignorieren.“

## 0. Installation

- [ ] `./install.sh` läuft ohne Fehler und ohne `sudo`
- [ ] Thunderbird-Erweiterung aus Datei installiert, Firefox-Erweiterung (signiert) installiert
- [ ] Roundcube-Adressen in den Einstellungen der Firefox-Erweiterung eingetragen
- [ ] `systemctl --user status kuchenmail-guard-notifier` zeigt „active (running)“

## 1. Pro Client

Für **Thunderbird**, **Gmail**, **Outlook Firma**, **Outlook privat** und **jede Roundcube-Instanz** (dort einmal HTML-, einmal Klartext-Editor):

| Schritt | Erwartet | TB | Gmail | OL Firma | OL privat | RC |
|---|---|---|---|---|---|---|
| Normale Mail senden | geht ohne Dialog raus | | | | | |
| Kuchenmail, Senden klicken | Passwortdialog erscheint | | | | | |
| … Abbrechen | Mail bleibt als Entwurf offen | | | | | |
| … richtiges Passwort | Mail geht raus | | | | | |
| … 3× falsches Passwort | Entwurf weg, Bildschirm gesperrt | | | | | |
| Kuchenmail mit Strg+Enter | Passwortdialog erscheint | | | | | |
| Antwort auf eine Kuchenmail („Danke!“) | geht ohne Dialog raus | | | | | |
| Outlook: Inline-Antwort im Lesebereich | Passwortdialog erscheint | – | – | | | – |

## 2. Benachrichtigung

- [ ] Nach einem abgebrochenen Versuch: Bildschirm sperren (Super+L), entsperren → Meldung „Kuchenmail abgefangen“ mit Uhrzeit und Betreff
- [ ] Nach dem 3×-falsch-Test: beim Entsperren erscheint die Meldung
- [ ] Erneut sperren/entsperren → keine doppelte Meldung
- [ ] Abmelden, anmelden → Dienst läuft wieder

## 3. Fehlerfälle

- [ ] Host weg: `mv ~/.local/share/kuchenmail-guard/bin/kuchenmail-guard-host{,.bak}` → Senden in Thunderbird und Gmail wird blockiert, Hinweis erscheint; danach zurückbenennen
- [ ] Kaputte Regeldatei (`echo "threshold = = 1" >> ~/.config/kuchenmail-guard/rules.toml`) → Erkennung läuft weiter, Warnung in `~/.local/state/kuchenmail-guard/guard.log`; danach Zeile entfernen
- [ ] `lock_on_detect = true` in `rules.toml` → beim Tippen einer Kuchenmail sperrt der Bildschirm innerhalb weniger Sekunden, nach dem Entsperren nicht erneut

## 4. Datenschutz und Ressourcen

- [ ] Während eine Kuchenmail-Prüfung läuft: `ss -tunp | grep -i kuchenmail` zeigt nichts
- [ ] `stat -c %a ~/.local/state/kuchenmail-guard/attempts.jsonl` zeigt `600`
- [ ] `attempts.jsonl` enthält Betreff und Empfänger, aber keinen Mailtext
- [ ] `ps -o rss,pcpu -C kuchenmail-guard-notifier` (bzw. `pgrep -f notifier`): unter 50 MB, unter 1 % CPU
