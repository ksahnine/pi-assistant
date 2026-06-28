#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installation du kiosk transport (IR) ==="

if [ ! -f /proc/device-tree/model ]; then
  echo "Ce script est conçu pour un Raspberry Pi." >&2
  exit 1
fi

echo "--- Dépendances ---"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  chromium-browser \
  jq \
  unclutter \
  x11-xserver-utils \
  python3-requests \
  python3-websocket \
  python3-evdev \
  ir-keytable

echo "--- Droits peripheriques ---"
sudo usermod -a -G video,input pi

echo "--- Permission backlight sysfs (udev) ---"
UDEV_RULE='/etc/udev/rules.d/99-backlight.rules'
if [ ! -f "$UDEV_RULE" ]; then
  echo 'SUBSYSTEM=="backlight", KERNEL=="10-0045", GROUP="video", MODE="0664"' | \
    sudo tee "$UDEV_RULE" > /dev/null
  sudo udevadm control --reload-rules
  sudo udevadm trigger
  echo "  -> règle udev créée"
else
  echo "  -> déjà présente"
fi

echo "--- Driver récepteur IR ---"
IR_PIN=$(jq -r '.ir.gpio_pin // 18' "$DIR/config.json")
CONFIG_FILE="/boot/firmware/config.txt"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="/boot/config.txt"
OVERLAY="gpio-ir"
if grep -q "gpio-ir-recv" "$CONFIG_FILE" 2>/dev/null; then
  OVERLAY="gpio-ir-recv"
fi
if ! grep -q "gpio-ir" "$CONFIG_FILE" 2>/dev/null; then
  echo "dtoverlay=$OVERLAY,gpio_pin=$IR_PIN" | sudo tee -a "$CONFIG_FILE"
  echo "  -> dtoverlay ajouté à $CONFIG_FILE (redémarrage requis)"
else
  echo "  -> déjà présent dans $CONFIG_FILE"
fi

echo "--- Kiosk optimisé (override LXDE-pi autostart) ---"
AUTOSTART_DIR="/home/pi/.config/lxsession/LXDE-pi"
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/autostart" << 'EOF'
@unclutter -idle 0.1 -root
EOF
chown -R pi:pi "/home/pi/.config/lxsession"
echo "  -> LXDE-pi allégé (plus de bureau/panneau)"

echo "--- Copie ---"
TARGET="/home/pi/transport-display"
mkdir -p "$TARGET"
cp "$DIR/config.json" "$DIR/start-kiosk.sh" "$DIR/gpio-monitor.py" "$DIR/discover-ir.py" "$TARGET/"
chmod +x "$TARGET/start-kiosk.sh" "$TARGET/gpio-monitor.py" "$TARGET/discover-ir.py"

echo "--- Services systemd ---"
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
Description=Transport IR Monitor
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

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Câblage HX1838 (GPIO $IR_PIN) :"
echo "  OUT (pin 1)  --> GPIO $IR_PIN"
echo "  GND (pin 2)  --> GND"
echo "  VCC (pin 3)  --> 3.3V (pin 1)"
echo ""
echo "Découvrir les codes IR :"
echo "  sudo ir-keytable -t"
echo "Puis éditer ir.keymap dans config.json"
echo ""
echo "Redémarrage : sudo reboot"
