#!/bin/sh
# Installiert Kuchenmail-Guard für den aktuellen Nutzer (ohne Root).
set -eu

SRC=$(cd "$(dirname "$0")" && pwd)
SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/kuchenmail-guard"
BIN="$HOME/.local/bin"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/kuchenmail-guard"
HOST_NAME="kuchenmail_guard"
MANIFEST_DIRS="$HOME/.mozilla/native-messaging-hosts $HOME/.thunderbird/native-messaging-hosts"

say() { printf '%s\n' "$*"; }

if ! /usr/bin/python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
  say "Fehler: /usr/bin/python3 in Version 3.11 oder neuer wird benötigt." >&2
  exit 1
fi
command -v zenity >/dev/null 2>&1 || say "Warnung: zenity fehlt, ohne Passwortdialog werden verdächtige Mails immer blockiert (sudo dnf install zenity)."

# Programm
rm -rf "$SHARE/guard" "$SHARE/bin"
mkdir -p "$SHARE" "$BIN"
cp -R "$SRC/guard" "$SRC/bin" "$SHARE/"
find "$SHARE/guard" -name '__pycache__' -type d -prune -exec rm -rf {} +
chmod 755 "$SHARE/bin/"*
ln -sf "$SHARE/bin/kuchenmail-guard-host" "$BIN/kuchenmail-guard-host"
say "Programm:    $SHARE"

# Native-Messaging-Manifeste für Firefox und Thunderbird
for dir in $MANIFEST_DIRS; do
  mkdir -p "$dir"
  sed "s|@HOST_PATH@|$SHARE/bin/kuchenmail-guard-host|" "$SRC/packaging/native-manifest.json.in" > "$dir/$HOST_NAME.json"
  say "Manifest:    $dir/$HOST_NAME.json"
done

# Regeldatei nur anlegen, wenn noch keine existiert
mkdir -p "$CONFIG"
if [ ! -e "$CONFIG/rules.toml" ]; then
  cp "$SRC/packaging/rules.toml.template" "$CONFIG/rules.toml"
  say "Regeln:      $CONFIG/rules.toml (neu angelegt)"
else
  say "Regeln:      $CONFIG/rules.toml (unverändert)"
fi

# Erweiterungen packen
build_xpi() {
  out="$SHARE/$2"
  rm -f "$out"
  (cd "$SRC/extensions/$1" && /usr/bin/python3 -m zipfile -c "$out" $(ls))
  say "Erweiterung: $out"
}
build_xpi thunderbird kuchenmail-guard-thunderbird.xpi
if [ -d "$SRC/extensions/webmail" ]; then
  signed=$(ls "$SRC"/dist/*.xpi 2>/dev/null | tail -n 1 || true)
  if [ -n "$signed" ]; then
    cp "$signed" "$SHARE/kuchenmail-guard-webmail.xpi"
    say "Erweiterung: $SHARE/kuchenmail-guard-webmail.xpi (signiert)"
  else
    say "Hinweis:     Keine signierte Firefox-Erweiterung in dist/ gefunden (make sign-webmail)."
  fi
fi

# Benachrichtigungsdienst
if [ -f "$SRC/packaging/kuchenmail-guard-notifier.service" ] && command -v systemctl >/dev/null 2>&1; then
  UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  mkdir -p "$UNIT_DIR"
  sed "s|@SHARE@|$SHARE|" "$SRC/packaging/kuchenmail-guard-notifier.service" > "$UNIT_DIR/kuchenmail-guard-notifier.service"
  if systemctl --user daemon-reload 2>/dev/null && systemctl --user enable --now kuchenmail-guard-notifier.service 2>/dev/null; then
    say "Dienst:      kuchenmail-guard-notifier.service (aktiv)"
  else
    say "Hinweis:     Dienst angelegt, aber nicht gestartet (systemctl --user enable --now kuchenmail-guard-notifier)."
  fi
fi

cat <<TEXT

Fertig. Noch zu tun (einmalig):

Thunderbird:  Add-ons und Themes → Zahnrad → „Add-on aus Datei installieren“ →
              $SHARE/kuchenmail-guard-thunderbird.xpi
TEXT
if [ -e "$SHARE/kuchenmail-guard-webmail.xpi" ]; then
  cat <<TEXT
Firefox:      Datei → Datei öffnen → $SHARE/kuchenmail-guard-webmail.xpi
              Danach in den Einstellungen der Erweiterung deine Roundcube-Adressen eintragen.
TEXT
fi
