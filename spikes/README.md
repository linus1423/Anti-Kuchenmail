# Spike T2: Eingriffspunkte prüfen

Dauer: etwa 20 Minuten. Es wird nichts dauerhaft installiert, und keine Mail geht raus, solange du nicht ausdrücklich freigibst. Nimm als Empfänger am besten dich selbst.

## Vorbereitung

```sh
git clone https://github.com/linus1423/Anti-Kuchenmail.git
cd Anti-Kuchenmail
./spikes/host/install-spike-host.sh
```

Alle Funde landen in `~/kuchenmail-spike.log`.

## A. Thunderbird

1. Thunderbird → Add-ons und Themes → Zahnrad → „Add-ons debuggen“ → „Temporäres Add-on laden“ → `spikes/thunderbird/manifest.json`.
2. Neue Mail an dich selbst, Betreff `Spike 1`, etwas Text, **Senden**. Die Mail sollte 30 Sekunden hängen und dann rausgehen.
3. Neue Mail, Betreff `SPIKE-CANCEL`, **Senden**. Nach 30 Sekunden sollte der Versand abgebrochen werden und das Fenster offen bleiben.
4. Eine Antwort auf eine vorhandene Mail (mit Zitat) mit Betreff `SPIKE-CANCEL` senden.

## B. Firefox (Gmail, Outlook, Roundcube)

1. `about:debugging#/runtime/this-firefox` → „Temporäres Add-on laden“ → `spikes/webmail/manifest.json`.
2. Für **Gmail**, **Outlook (Firma)**, **Outlook (privat)** und **jede Roundcube-Instanz**:
   1. Postfach öffnen (Seite neu laden, falls sie schon offen war).
   2. Neue Mail an dich selbst mit Betreff `Spike` und dem Text „Ich bringe morgen Kuchen mit“.
   3. Auf **Senden** klicken. Erwartet: nichts passiert (blockiert).
   4. Noch einmal mit **Strg+Enter** versuchen. Erwartet: blockiert.
   5. **Alt** gedrückt halten und auf Senden klicken. Erwartet: Mail geht raus.
   6. Bei Outlook zusätzlich: dasselbe als **Antwort im Lesebereich** (Inline-Antwort).
   7. Bei Roundcube zusätzlich: einmal im HTML-Editor und einmal im Klartext-Editor.

## Ergebnis zurückgeben

Schick mir den Inhalt von `~/kuchenmail-spike.log` (Mailtexte darin sind nur deine Testmails) und kurz pro Client, ob Blockieren und Freigeben geklappt haben.

## Aufräumen

```sh
rm ~/.mozilla/native-messaging-hosts/kuchenmail_spike.json ~/.thunderbird/native-messaging-hosts/kuchenmail_spike.json ~/kuchenmail-spike.log
```

Temporäre Add-ons verschwinden beim nächsten Neustart von selbst.
