# Pi-Assistant Transport Kiosk

Affichage des horaires de transport en commun sur Raspberry Pi 3 + écran DSI tactile,
avec entrée configurable : boutons GPIO ou télécommande IR.

## Architecture

```
                          config.json
                              │
              ┌───────────────┴───────────────┐
              │            input.method        │
         method=gpio                   method=ir
              │                              │
    RPi.GPIO (pins)            gpio-ir-recv (kernel)
              │                    python-evdev
              │                              │
              └───────────┬──────────────────┘
                          │
                   event_queue (thread-safe)
                          │
              ┌───────────┴───────────┐
              │                       │
       Page.navigate (CDP)    vcgencmd display_power
              │                       │
         Chromium 9222           écran ON/OFF
```

Deux méthodes d'entrée possibles, une seule active à la fois.

## Arborescence

```
/home/pi/transport-display/
├── config.json           # Tout le projet : display, screens, input
├── start-kiosk.sh        # Lance Chromium en kiosk (port 9222)
├── gpio-monitor.py       # Input GPIO ou IR + navigation CDP
└── install.sh            # Installation complète
```

## Câblage

### Mode GPIO (input.method = "gpio")

Pull-up interne, chaque broche → bouton → GND.

```
GPIO 17 ──┬─── bouton navigate screen[0] ─── GND
GPIO 22 ──┬─── bouton navigate screen[1] ─── GND
GPIO 23 ──┬─── bouton navigate screen[2] ─── GND
GPIO 27 ──┬─── bouton power (veille) ──────── GND
```

### Mode IR (input.method = "ir")

```
TSOP38238 / VS1838B      RPi GPIO
┌────────────────┐
│ OUT  ──────────┼──── GPIO 18
│ VCC  ──────────┼──── 3.3V (pin 1)
│ GND  ──────────┼──── GND
└────────────────┘
```

## Installation

### 1. Prérequis

- Raspberry Pi 3 avec Raspberry Pi OS Desktop
- Écran officiel RPi Touch DSI
- Connexion WiFi ou ethernet
- SSH activé

### 2. Copier les fichiers

```bash
scp -r transport-display/ pi@<ip-du-rpi>:/home/pi/
```

### 3. Installer

```bash
ssh pi@<ip-du-rpi>
cd /home/pi/transport-display
chmod +x install.sh start-kiosk.sh gpio-monitor.py
./install.sh
```

### 4. Redémarrer

```bash
sudo reboot
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
    { "name": "RER Magenta",     "url": "https://monrer.fr/?s=MGT" },
    { "name": "RER Paris Nord",  "url": "https://monrer.fr/?s=GDS" },
    { "name": "Metro / Bus",     "url": "https://departs.leon.gp/..." }
  ],

  "default_screen": 0,

  "power": { "name": "Veille" },

  "input": {
    "method": "ir",
    "gpio": {
      "pins": [
        { "gpio_pin": 17, "action": "navigate", "screen": 0 },
        { "gpio_pin": 22, "action": "navigate", "screen": 1 },
        { "gpio_pin": 23, "action": "navigate", "screen": 2 },
        { "gpio_pin": 27, "action": "power" }
      ]
    },
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
}
```

### Découvrir les codes IR

Après installation et redémarrage :

```bash
sudo ir-keytable -t
```

Appuyez sur les touches de votre télécommande. Notez les codes `KEY_*` affichés,
puis renseignez-les dans `input.ir.keymap`.

Redémarrez le service :

```bash
sudo systemctl restart transport-gpio
```

### Basculer entre GPIO et IR

Changer `"method": "gpio"` ↔ `"method": "ir"` dans `config.json`,
redémarrer le service. Les deux configurations restent dans le fichier.

## Services systemd

| Service | Rôle |
|---------|------|
| `transport-kiosk.service` | Chromium en kiosk |
| `transport-gpio.service` | Input monitor (GPIO ou IR) |

```bash
journalctl -u transport-kiosk -f
journalctl -u transport-gpio -f
```
