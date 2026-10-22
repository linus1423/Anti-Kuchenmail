# Anforderungen: Kuchenmail-Guard

> Status: Freigegeben (2026-10-22), geändert 2026-10-22: Roundcube und Outlook im Web ergänzt (R4.6, R4.7)

## Ziel

Wenn Linus seinen Fedora-Rechner kurz entsperrt stehen lässt, schreiben Kollegen gern in seinem Namen eine Mail wie „Ich bringe morgen Kuchen mit“. Das Tool erkennt solche Mails automatisch, während sie geschrieben werden, und verhindert den Versand, ohne dass Daten den Rechner verlassen.

## Nutzer & Rollen

| Rolle | Beschreibung |
|---|---|
| Besitzer (Linus) | Einziger legitimer Nutzer; will nie wieder eine Kuchenmail „schicken“ und keine Fehlalarme bei normalen Mails |
| Angreifer (Kollege) | Sitzt am entsperrten Rechner und versucht, eine Kuchenmail zu schreiben und abzusenden; kennt Linus' Passwort nicht |

## Anforderungen

### R1: Kuchenmail erkennen

**User Story:** Als Besitzer möchte ich, dass eine Kuchenmail schon beim Schreiben erkannt wird, damit sie gar nicht erst rausgeht.

**Akzeptanzkriterien**

- **R1.1** WENN in einer neu verfassten Mail (Betreff oder Text) eine Ankündigung erkannt wird, Essen oder Getränke für andere mitzubringen oder auszugeben (z. B. Kuchen, Torte, Muffins, Brötchen, Pizza, Eis, „Runde ausgeben“), DANN SOLL das System die Mail als Kuchenmail-Verdacht markieren.
- **R1.2** Das System SOLL die Erkennung spätestens beim Auslösen von „Senden“ abschließen.
- **R1.3** WENN die Mail an mehr als 3 Empfänger oder an einen Verteiler adressiert ist, DANN SOLL das System dies als zusätzliches Verdachtsmerkmal werten.
- **R1.4** Das System SOLL deutsche und englische Formulierungen erkennen.
- **R1.5** FALLS eine Mail nur zitierten Text einer empfangenen Mail mit Kuchen-Bezug enthält (Antwort/Weiterleitung), DANN SOLL das System nur den neu geschriebenen Teil bewerten.

### R2: Versand abfangen

**User Story:** Als Besitzer möchte ich, dass eine verdächtige Mail nur mit meinem Passwort versendet werden kann, damit ein Kollege sie nicht abschicken kann, ich aber echte Kuchenmails trotzdem senden kann.

**Akzeptanzkriterien**

- **R2.1** WENN eine als Verdacht markierte Mail gesendet werden soll, DANN SOLL das System den Versand anhalten und einen Bestätigungsdialog anzeigen.
- **R2.2** WENN im Dialog das Linux-Passwort des Besitzers korrekt eingegeben wird, DANN SOLL das System die Mail unverändert versenden.
- **R2.3** WENN der Dialog abgebrochen wird, DANN SOLL das System die Mail nicht versenden und als Entwurf behalten.
- **R2.4** FALLS das Passwort 3-mal falsch eingegeben wird, DANN SOLL das System die Mail verwerfen und den Bildschirm sperren.
- **R2.5** Das System SOLL eine nicht als Verdacht markierte Mail ohne Verzögerung oder Dialog versenden.

### R3: Benachrichtigung und Protokoll

**User Story:** Als Besitzer möchte ich erfahren, wenn jemand es versucht hat, damit ich weiß, wer mir Kuchen schuldet.

**Akzeptanzkriterien**

- **R3.1** WENN ein Versand abgefangen wurde, DANN SOLL das System einen Eintrag mit Zeitstempel, Empfängern, Betreff und Ausgang (abgebrochen / freigegeben / gesperrt) in eine lokale Logdatei schreiben.
- **R3.2** WENN der Besitzer sich nach einem abgefangenen Versuch wieder anmeldet bzw. den Bildschirm entsperrt, DANN SOLL das System eine Desktop-Benachrichtigung mit Uhrzeit und Betreff des Versuchs anzeigen.
- **R3.3** Das System SOLL die Logdatei nur für den Besitzer lesbar ablegen (Dateirechte 0600).

### R4: Konfiguration und Betrieb

**User Story:** Als Besitzer möchte ich die Erkennung anpassen und das Tool vergessen können, damit es einfach im Hintergrund läuft.

**Akzeptanzkriterien**

- **R4.1** Das System SOLL Schlüsselwörter und Muster aus einer lokalen, menschenlesbaren Konfigurationsdatei laden.
- **R4.2** WENN die Konfigurationsdatei geändert wird, DANN SOLL das System die neuen Regeln spätestens beim nächsten Erkennungsvorgang verwenden, ohne Neustart.
- **R4.3** FALLS die Konfigurationsdatei fehlt oder fehlerhaft ist, DANN SOLL das System mit eingebauten Standardregeln weiterlaufen und eine Warnung ins Log schreiben.
- **R4.4** Das System SOLL nach der Anmeldung automatisch starten.
- **R4.5** WO der Schalter „Bildschirm bei Verdacht sofort sperren“ aktiviert ist, SOLL das System den Bildschirm bereits beim Erkennen (R1.1) sperren, nicht erst beim Senden.
- **R4.6** Das System SOLL neben Thunderbird und Gmail auch Roundcube-Webmail unter einer oder mehreren vom Besitzer konfigurierten Adressen abdecken.
- **R4.7** Das System SOLL Outlook im Web (Microsoft 365 und privates Outlook.com) abdecken.

## Nicht-funktionale Anforderungen

| ID | Kategorie | Anforderung (messbar) |
|---|---|---|
| N1 | Datenschutz | Das Tool baut keine Netzwerkverbindungen auf und sendet keine Telemetrie; prüfbar mit `ss -tunp` bzw. einem Test ohne Netzwerkzugriff. Mailinhalte werden nicht gespeichert, nur Betreff und Empfänger im Log. |
| N2 | Treffsicherheit | Auf einem Test-Korpus von mind. 30 Kuchenmails werden ≥ 95 % erkannt. |
| N3 | Fehlalarme | Auf einem Test-Korpus von mind. 50 normalen Arbeitsmails (inkl. Mails, die Essen nur erwähnen) gibt es ≤ 2 Fehlalarme. |
| N4 | Performance | Erkennung einer Mail bis 10 kB Text dauert < 200 ms; Senden ohne Verdacht wird um < 100 ms verzögert. |
| N5 | Ressourcen | Hintergrundprozess braucht < 50 MB RAM und im Leerlauf < 1 % CPU. |
| N6 | Installation | Installation auf aktuellem Fedora (Workstation, GNOME, Wayland) mit einem Befehl ohne Root-Rechte, Deinstallation ebenso. |
| N7 | Sicherheit | Der Freigabe-Dialog prüft das Passwort über das System (PAM/polkit); das Tool speichert kein eigenes Passwort. |

## Randbedingungen

- Fedora Linux, aktuelle Version, GNOME auf Wayland.
- Mail-Clients: Thunderbird sowie Gmail, Roundcube und Outlook als Webmail im Browser (**Annahme:** Firefox).
- Einzelner Nutzer, einzelner Rechner, keine Server-Komponente.
- Keine Vorgabe zur Programmiersprache.
- Keine Deadline.

## Nicht im Umfang (Out of Scope)

- Andere Betriebssysteme, mehrere Nutzer oder zentraler Rollout.
- Mails, die von anderen Geräten (Handy, anderer PC) gesendet werden.
- Andere Streiche am entsperrten Rechner (Hintergrundbild, Chat-Nachrichten in Teams/Slack).
- Automatisches Sperren beim Verlassen des Platzes (Bluetooth-Proximity o. Ä.).
- Cloud- oder KI-Dienste zur Erkennung.
- Erkennen von Kuchenmails in empfangenen Mails.

## Offene Fragen

- [x] Mail-Clients: Thunderbird, Gmail, Roundcube und Outlook im Browser (geklärt 2026-10-22).
- [x] GNOME auf Wayland, Freigabe per Linux-Passwort (bestätigt 2026-10-22).
- [ ] **Annahme:** Alle Webmailer laufen in Firefox, nicht in Chrome/Chromium. — Linus
- [ ] Unter welcher Adresse läuft dein Roundcube (z. B. `webmail.example.de`), und welche Version bzw. welches Skin? — Linus
- [ ] Outlook im Web: Firmenkonto (Microsoft 365), privates Outlook.com oder beides? Oberfläche auf Deutsch oder Englisch? — Linus
- [ ] Sollen auch Chat-Tools (Teams, Slack) abgedeckt werden? Aktuell Out of Scope. — Linus
