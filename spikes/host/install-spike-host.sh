#!/bin/sh
# Registriert den Spike-Host für Firefox und Thunderbird (nur aktueller Nutzer).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
host="$here/spike_host.py"
for dir in "$HOME/.mozilla/native-messaging-hosts" "$HOME/.thunderbird/native-messaging-hosts"; do
  mkdir -p "$dir"
  cat > "$dir/kuchenmail_spike.json" <<JSON
{
  "name": "kuchenmail_spike",
  "description": "Kuchenmail-Guard Spike",
  "path": "$host",
  "type": "stdio",
  "allowed_extensions": ["spike-thunderbird@kuchenmail-guard", "spike-webmail@kuchenmail-guard"]
}
JSON
  echo "Manifest: $dir/kuchenmail_spike.json"
done
