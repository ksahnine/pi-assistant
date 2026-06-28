# Pi-Assistant Transport Kiosk

Affichage des horaires de transport en commun sur Raspberry Pi 3 + écran DSI tactile,
piloté par télécommande IR.

## Architecture

```
Télécommande IR
      │
      ▼
HX1838 ── GPIO 18
      │
gpio-ir (kernel overlay)
      │
python-evdev ── gpio-monitor.py
      │              │
      ├── Chromium CDP (Page.navigate)
      └── vcgencmd (display_power ON/OFF)
```

## Arborescence

```
/home/pi/transport-display/
├── config.json           # Configuration : écrans, IR keymap
├── start-kiosk.sh        # Lance Chromium en kiosk (port 9222)
├── gpio-monitor.py       # Surveille IR, navigue CDP + veille
├── discover-ir.py        # Outil : détecter les codes de la télécommande
└── install.sh            # Installation complète
```

## Câblage

Brancher le récepteur **HX1838** sur le GPIO 18 (pin physique 12) :

```
HX1838 (face plate vers vous, pattes vers le bas)

┌────────────┐
│    ●       │  ← récepteur IR
│ OUT GND VCC│
└────────────┘
  │    │    │
  │    │    └── 3.3V (pin 1)
  │    └─────── GND (pin 6)
  └──────────── GPIO 18 (pin 12)
```

## Installation

```bash
# Copier les fichiers sur le RPi
scp -r transport-display/ pi@<ip-du-rpi>:/home/pi/

# Installer
ssh pi@<ip-du-rpi>
cd /home/pi/transport-display
chmod +x install.sh start-kiosk.sh gpio-monitor.py
./install.sh

# Redémarrer
sudo reboot
```

## Découvrir les codes IR de la télécommande

```bash
sudo python3 /home/pi/transport-display/discover-ir.py
```

Appuyez sur les touches de la télécommande. Notez les `KEY_*` affichés
et reportez-les dans la section `ir.keymap` du fichier `config.json`.

Redémarrez le service :
```bash
sudo systemctl restart transport-gpio
```

## Configuration

Éditer `/home/pi/transport-display/config.json` :

```json
{
  "display": {
    "hide_cursor": true,
    "touch_enabled": true,
    "overlay_duration_seconds": 2
  },
  "screens": [
    { "name": "RER Magenta",   "url": "https://monrer.fr/?s=MGT" },
    { "name": "RER Paris Nord", "url": "https://monrer.fr/?s=GDS" },
    { "name": "Metro / Bus",   "url": "https://departs.leon.gp/..." }
  ],
  "default_screen": 0,
  "power": { "name": "Veille" },
  "ir": {
    "gpio_pin": 18,
    "keymap": {
      "KEY_1":     { "action": "navigate", "screen": 0 },
      "KEY_2":     { "action": "navigate", "screen": 1 },
      "KEY_3":     { "action": "navigate", "screen": 2 },
      "KEY_POWER": { "action": "power" }
    }
  }
}
```

## Services systemd

| Service | Rôle |
|---------|------|
| `transport-kiosk.service` | Chromium en kiosk |
| `transport-gpio.service` | IR monitor |

```bash
journalctl -u transport-kiosk -f
journalctl -u transport-gpio -f
```
