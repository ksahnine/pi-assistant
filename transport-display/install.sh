#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installation du kiosk transport ==="

# 1. Vérifier qu'on est sur un RPi
if [ ! -f /proc/device-tree/model ]; then
  echo "Ce script est conçu pour un Raspberry Pi." >&2
  exit 1
fi

# 2. Installer les dépendances de base
echo "--- Installation des dépendances ---"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  chromium-browser \
  jq \
  unclutter \
  x11-xserver-utils \
  python3-requests \
  python3-websocket

# 3. Dépendances selon la méthode d'entrée
METHOD=$(jq -r '.input.method' "$DIR/config.json")
echo "--- Méthode d'entrée: $METHOD ---"

if [ "$METHOD" = "gpio" ]; then
  sudo apt-get install -y -qq python3-rpi.gpio
elif [ "$METHOD" = "ir" ]; then
  sudo apt-get install -y -qq \
    ir-keytable \
    python3-evdev

  IR_PIN=$(jq -r '.input.ir.gpio_pin // 18' "$DIR/config.json")
  if ! grep -q "gpio-ir-recv" /boot/config.txt 2>/dev/null; then
    echo "dtoverlay=gpio-ir-recv,gpio_pin=$IR_PIN" | sudo tee -a /boot/config.txt
    echo "  -> dtoverlay ajouté à /boot/config.txt (redémarrage requis)"
  else
    echo "  -> dtoverlay déjà présent dans /boot/config.txt"
  fi
fi

# 4. Ajouter pi au groupe video (pour vcgencmd display_power)
echo "--- Droits vcgencmd ---"
sudo usermod -a -G video pi

# 5. Créer le répertoire de destination
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

# 6. Créer les services systemd
echo "--- Configuration des services systemd ---"

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

sudo tee /etc/systemd/system/transport-gpio.service > /dev/null <<EOF
[Unit]
Description=Transport Input Monitor (GPIO/IR)
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

# 7. Notifier
echo ""
echo "=== Installation terminée ==="
echo ""

if [ "$METHOD" = "gpio" ]; then
  echo "Câblage des boutons (pull-up interne) :"
  for pin in $(jq -r '.input.gpio.pins[] | "GPIO " + (.gpio_pin|tostring) + " --> " + .action' "$TARGET/config.json"); do
    echo "  $pin"
  done
elif [ "$METHOD" = "ir" ]; then
  VDD_PIN=$((IR_PIN - 1))
  GND_PIN=$((IR_PIN + 2))
  echo "Câblage récepteur IR (GPIO $IR_PIN) :"
  echo "  OUT  --> GPIO $IR_PIN"
  echo "  VCC  --> 3.3V (pin 1)"
  echo "  GND  --> GND"
  echo ""
  echo "Après redémarrage, découvrez les codes de votre télécommande :"
  echo "  sudo ir-keytable -t"
  echo "Puis éditez input.ir.keymap dans config.json"
fi

echo ""
echo "Redémarrez le RPi :"
echo "  sudo reboot"
