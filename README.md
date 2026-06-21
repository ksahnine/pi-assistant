# Pi-Assistant Transport Kiosk

Affichage des horaires de transport en commun sur Raspberry Pi 3 + écran DSI tactile,
avec boutons poussoirs GPIO pour basculer entre plusieurs lignes/arrêts.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Raspberry Pi                      │
│                                                      │
│  gpio-monitor.py ─── GPIO ─── boutons poussoirs     │
│       │                                              │
│       ├── WebSocket ──► Chromium DevTools API        │
│       │    (Page.navigate + Runtime.evaluate)        │
│       │                                              │
│  Chromium ─── kiosk ─── remote-debugging-port 9222   │
│                                                      │
│  start-kiosk.sh ──► lance Chromium                   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

Chaque appui sur un bouton déclenche :
1. `Page.navigate` vers l'URL associée (via CDP, **sans redémarrage ni flash**)
2. Un toast overlay avec le nom de la ligne (2s puis disparaît)

## Arborescence

```
/home/pi/transport-display/
├── config.json           # URLs, GPIO pins, options (nav + power)
├── start-kiosk.sh        # Lance Chromium en kiosk (port 9222)
├── gpio-monitor.py       # Surveille les GPIO, navigue CDP + toggle écran
└── install.sh            # Installation complète
```

## Câblage des boutons

Pull-up interne activé dans le script (pas de résistance externe).

```
GPIO 17 ──┬─── bouton nav 1 ─── GND
GPIO 22 ──┬─── bouton nav 2 ─── GND
GPIO 23 ──┬─── bouton nav 3 ─── GND
GPIO 27 ──┬─── bouton veille ─── GND
```

Brancher chaque bouton entre le GPIO et un pin GND du RPi.

Le bouton **veille** (GPIO 27) bascule l'écran ON/OFF via `vcgencmd display_power`.
Chromium continue de tourner en arrière-plan, l'affichage revient instantanément.

## Installation

### 1. Prérequis

- Raspberry Pi 3 avec Raspberry Pi OS Desktop installé
- Écran officiel RPi Touch DSI
- Connexion WiFi (ou ethernet)
- SSH activé

### 2. Copier les fichiers

```bash
scp -r transport-display/ pi@<ip-du-rpi>:/home/pi/
```

### 3. Lancer l'installation

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
  "hide_cursor": true,
  "touch_enabled": true,
  "overlay_duration_seconds": 2,
  "default_url": "https://...",
  "buttons": [
    {
      "gpio_pin": 17,
      "name": "Bus 56",
      "url": "https://departs.leon.gp/screen/?screenId=bus&stopId=..."
    },
    {
      "gpio_pin": 22,
      "name": "Metro 1",
      "url": "https://departs.leon.gp/screen/?screenId=metro&stopId=..."
    }
  ],
  "power_button": {
    "gpio_pin": 27,
    "name": "Veille"
  }
}
```

Puis redémarrer les services :

```bash
sudo systemctl restart transport-kiosk transport-gpio
```

## Maintenance

| Commande | Action |
|----------|--------|
| `ssh pi@<ip-du-rpi>` | Connexion SSH |
| `journalctl -u transport-kiosk -f` | Logs Chromium |
| `journalctl -u transport-gpio -f` | Logs GPIO |
| `sudo systemctl stop transport-kiosk transport-gpio` | Arrêt |
| `sudo systemctl disable transport-kiosk transport-gpio` | Désactiver au boot |

## Services systemd

| Service | Rôle |
|---------|------|
| `transport-kiosk.service` | Chromium en kiosk |
| `transport-gpio.service` | Surveillance boutons (dépend de kiosk) |
