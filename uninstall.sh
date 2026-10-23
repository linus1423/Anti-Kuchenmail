#!/bin/sh
# Entfernt Kuchenmail-Guard. Log und eigene Regeln bleiben erhalten.
set -eu

SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/kuchenmail-guard"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/kuchenmail-guard"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/kuchenmail-guard"
UNIT="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/kuchenmail-guard-notifier.service"

if [ -e "$UNIT" ]; then
  systemctl --user disable --now kuchenmail-guard-notifier.service 2>/dev/null || true
  rm -f "$UNIT"
  systemctl --user daemon-reload 2>/dev/null || true
fi
rm -f "$HOME/.mozilla/native-messaging-hosts/kuchenmail_guard.json" \
      "$HOME/.thunderbird/native-messaging-hosts/kuchenmail_guard.json" \
      "$HOME/.local/bin/kuchenmail-guard-host"
rm -rf "$SHARE"

cat <<TEXT
Kuchenmail-Guard entfernt.

Die Erweiterungen bitte noch in Thunderbird und Firefox unter Add-ons entfernen.
Erhalten geblieben sind (bei Bedarf selbst löschen):
  $CONFIG    (eigene Regeln)
  $STATE     (Protokoll der abgefangenen Versuche)
TEXT
