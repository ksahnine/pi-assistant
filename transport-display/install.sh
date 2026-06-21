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
  x11-xserver-utils \
  python3-requests \
  python3-websocket \
  python3-rpi.gpio

# 3. Ajouter pi au groupe video (pour vcgencmd display_power)
echo "--- Droits vcgencmd ---"
sudo usermod -a -G video pi

# 4. Créer le répertoire de destination si différent
if [ "$DIR" != "/home/pi/transport-display" ]; then
  mkdir -p /home/pi/transport-display
  cp "$DIR/config.json" /home/pi/transport-display/
  cp "$DIR/start-kiosk.sh" /home/pi/transport-display/
  cp "$DIR/gpio-monitor.py" /home/pi/transport-display/
  chmod +x /home/pi/transport-display/start-kiosk.sh
  chmod +x /home/pi/transport-display/gpio-monitor.py
  TARGET="/home/pi/transport-display"
else
  TARGET="$DIR"
fi

chmod +x "$TARGET/start-kiosk.sh" "$TARGET/gpio-monitor.py"

# 5. Créer les services systemd
echo "--- Configuration des services systemd ---"

# Service Chromium kiosk
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

# Service GPIO monitor
sudo tee /etc/systemd/system/transport-gpio.service > /dev/null <<EOF
[Unit]
Description=Transport GPIO Button Monitor
After=transport-kiosk.service
BindsTo=transport-kiosk.service

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/python3 $TARGET/gpio-monitor.py
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable transport-kiosk
sudo systemctl enable transport-gpio

# 6. Notifier
echo ""
echo "=== Installation terminée ==="
echo ""
echo "Câblage des boutons (pull-up interne, broche --- bouton --- GND) :"
for pin in $(jq -r '.buttons[].gpio_pin' "$TARGET/config.json"); do
  echo "  GPIO $pin --> bouton --> GND"
done
power_pin=$(jq -r '.power_button.gpio_pin // empty' "$TARGET/config.json")
if [ -n "$power_pin" ]; then
  echo "  GPIO $power_pin --> bouton (veille) --> GND"
fi
echo ""
echo "Redémarrez le RPi pour lancer le kiosk :"
echo "  sudo reboot"
echo ""
echo "Ou démarrez les services immédiatement :"
echo "  sudo systemctl start transport-kiosk"
echo "  sudo systemctl start transport-gpio"
echo ""
echo "Pour modifier les stations, éditez :"
echo "  $TARGET/config.json"
echo "Puis redémarrez les services :"
echo "  sudo systemctl restart transport-kiosk transport-gpio"
