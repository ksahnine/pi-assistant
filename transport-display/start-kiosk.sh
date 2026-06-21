#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$DIR/config.json"

if [ ! -f "$CONFIG" ]; then
  echo "config.json introuvable" >&2
  exit 1
fi

URL="$(jq -r '.url' "$CONFIG")"
HIDE_CURSOR="$(jq -r '.hide_cursor // true' "$CONFIG")"
TOUCH_ENABLED="$(jq -r '.touch_enabled // true' "$CONFIG")"

export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"

# Attendre que le serveur X soit prêt
for i in $(seq 1 30); do
  if xset q &>/dev/null; then
    break
  fi
  sleep 1
done

# Désactiver la mise en veille et l'économie d'énergie
xset s off
xset -dpms
xset s noblank

# Cacher le curseur
if [ "$HIDE_CURSOR" = "true" ]; then
  unclutter -idle 0.1 -root &
fi

# Flags Chromium
FLAGS=(
  --kiosk
  --noerrdialogs
  --disable-infobars
  --no-first-run
  --disable-restore-session-state
  --disable-translate
  --password-store=basic
  --disable-features=TranslateUI
  --disable-features=ChromeWhatsNewUI
  --disable-session-crashed-bubble
  --disable-component-update
  --no-crash-upload
  --no-default-browser-check
  --check-for-update-interval=604800
)

if [ "$TOUCH_ENABLED" = "true" ]; then
  FLAGS+=(--touch-events=enabled)
fi

# Forcer l'utilisation de Chromium (ou chromium-browser)
BROWSER=""
for cmd in chromium-browser chromium; do
  if command -v "$cmd" &>/dev/null; then
    BROWSER="$cmd"
    break
  fi
done

if [ -z "$BROWSER" ]; then
  echo "Chromium introuvable. Installez-le avec : sudo apt install chromium-browser" >&2
  exit 1
fi

exec "$BROWSER" "${FLAGS[@]}" "$URL"
