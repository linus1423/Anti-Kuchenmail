# Projektkontext (Steering)

> Status: Entwurf

| Thema | Stand |
|---|---|
| Zweck | Lokales Tool, das Kuchenmails (Streich-Mails von einem entsperrten Rechner) erkennt und abfängt |
| Nutzer | Nur Linus, ein Rechner |
| Plattform | Fedora Linux, GNOME auf Wayland; Mail über Thunderbird sowie Gmail, Roundcube und Outlook im Browser |
| Stack | Python 3 (nur Standardbibliothek) für Erkennung, Native-Messaging-Host und Hintergrunddienst; JavaScript-WebExtensions für Thunderbird und Firefox (Gmail, Roundcube, Outlook Web) |
| Datenschutz | Alles lokal, keine Netzwerkverbindungen, keine Telemetrie |
| Repo-Stand | Leer (nur README), Stand 2026-10-21 |
| Konventionen | Specs auf Deutsch, Code-Bezeichner englisch |
