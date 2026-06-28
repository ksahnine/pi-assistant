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

### Correspondance GPIO BCM / pin physique

Sur le connecteur 40 broches du RPi, le numéro GPIO (Broadcom) diffère du numéro de pin physique :

```
┌─────────────────────────────────┐
│                          CARTE  │
│ SD                            • │
├─────────────────────────────────┤
│  (1)  3.3V       5V  (2)       │
│  (3)  GPIO 2     5V  (4)       │
│  (5)  GPIO 3     GND (6)       │
│  (7)  GPIO 4    GPIO 14 (8)    │
│  (9)  GND       GPIO 15 (10)   │
│ (11)  GPIO 17   GPIO 18 (12)   │
│ (13)  GPIO 27   GND   (14)     │
│ (15)  GPIO 22   GPIO 23 (16)   │
│ (17)  3.3V      GPIO 24 (18)   │
│ (19)  GPIO 10   GND   (20)     │
│ (21)  GPIO 9    GPIO 25 (22)   │
│ (23)  GPIO 11   GPIO 8  (24)   │
│ (25)  GND       GPIO 7  (26)   │
│ (27)  GPIO 0    GPIO 1  (28)   │
│ (29)  GPIO 5    GND   (30)     │
│ (31)  GPIO 6    GPIO 12 (32)   │
│ (33)  GPIO 13   GND   (34)     │
│ (35)  GPIO 19   GPIO 16 (36)   │
│ (37)  GPIO 26   GPIO 20 (38)   │
│ (39)  GND       GPIO 21 (40)   │
└─────────────────────────────────┘
```

Pins utilisées par ce projet :

| GPIO BCM | Pin physique | Usage |
|----------|-------------|-------|
| 17       | 11          | Bouton / IR key screen[0] |
| 22       | 15          | Bouton / IR key screen[1] |
| 23       | 16          | Bouton / IR key screen[2] |
| 27       | 13          | Bouton power |
| 18       | 12          | Récepteur IR (OUT) |

### Mode GPIO (input.method = "gpio")

Pull-up interne, chaque broche → bouton → GND.

```
GPIO 17 ──┬─── bouton navigate screen[0] ─── GND
GPIO 22 ──┬─── bouton navigate screen[1] ─── GND
GPIO 23 ──┬─── bouton navigate screen[2] ─── GND
GPIO 27 ──┬─── bouton power (veille) ──────── GND
```

### Mode IR (input.method = "ir")

Brancher un récepteur **HX1838** (38 kHz, compatible avec toutes les télécommandes standard).

Vue du composant, face plate vers vous, pattes vers le bas :

```
HX1838
┌────────────┐
│    ●       │  ← récepteur IR
│ OUT GND VCC│
└────────────┘
  │    │    │
  │    │    └── 3.3V (pin 1)
  │    └─────── GND (pin 6)
  └──────────── GPIO 18
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
