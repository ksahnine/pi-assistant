#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installation du kiosk transport ==="

# 1. Vérifier qu'on est sur un RPi
if [ ! -f /proc/device-tree/model ]; then
  echo "Ce script est conçu pour un Raspberry Pi." >&2
  exit 1
fi

# 2. Installer les dépendances
echo "--- Installation des dépendances ---"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  chromium-browser \
  jq \
  unclutter \
  x11-xserver-utils

# 3. Créer le répertoire de destination si différent
if [ "$DIR" != "/home/pi/transport-display" ]; then
  mkdir -p /home/pi/transport-display
  cp "$DIR/config.json" /home/pi/transport-display/
  cp "$DIR/start-kiosk.sh" /home/pi/transport-display/
  chmod +x /home/pi/transport-display/start-kiosk.sh
  TARGET="/home/pi/transport-display"
else
  TARGET="$DIR"
fi

chmod +x "$TARGET/start-kiosk.sh"

# 4. Créer le service systemd
echo "--- Configuration du service systemd ---"

sudo tee /etc/systemd/system/transport-kiosk.service > /dev/null <<EOF
[Unit]
Description=Transport Kiosk
After=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStartPre=/usr/bin/sleep 5
ExecStart=$TARGET/start-kiosk.sh
Restart=always
RestartSec=10

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable transport-kiosk

# 5. Notifier
echo ""
echo "=== Installation terminée ==="
echo ""
echo "Redémarrez le RPi pour lancer le kiosk :"
echo "  sudo reboot"
echo ""
echo "Ou démarrez le service immédiatement :"
echo "  sudo systemctl start transport-kiosk"
echo ""
echo "Pour modifier la station, éditez :"
echo "  $TARGET/config.json"
echo "Puis redémarrez le service :"
echo "  sudo systemctl restart transport-kiosk"
