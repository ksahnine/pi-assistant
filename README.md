# Pi-Assistant Transport Kiosk

Affichage des horaires de transport en commun sur Raspberry Pi 3 + écran DSI tactile.

## Principe

Au démarrage, le RPi lance Chromium en mode kiosk sur une URL configurable affichant
les prochains passages d'une station de transport Île-de-France Mobilités.

Exemple d'URL : `https://departs.leon.gp/screen/?screenId=bus&stopId=fr-idf_IDFM:71434&lineId=fr-idf_IDFM:C01089`

## Arborescence

```
/home/pi/transport-display/
├── config.json          # URL et options d'affichage
├── start-kiosk.sh       # Script de lancement Chromium
└── install.sh           # Installation et configuration autostart
```

## Installation

### 1. Prérequis

- Raspberry Pi 3 avec Raspberry Pi OS Desktop installé
- Écran officiel RPi Touch DSI (reconnu automatiquement)
- Connexion WiFi configurée (ou ethernet)
- SSH activé pour la maintenance

### 2. Copier les fichiers sur le RPi

```bash
scp -r transport-display/ pi@<ip-du-rpi>:/home/pi/
```

### 3. Lancer l'installation

```bash
ssh pi@<ip-du-rpi>
cd /home/pi/transport-display
chmod +x install.sh start-kiosk.sh
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
  "url": "https://departs.leon.gp/screen/?screenId=bus&stopId=fr-idf_IDFM:71434&lineId=fr-idf_IDFM:C01089",
  "hide_cursor": true,
  "touch_enabled": true
}
```

Pour changer de station, modifier l'URL et redémarrer le service :

```bash
sudo systemctl restart transport-kiosk
```

## Maintenance

- **SSH** : `ssh pi@<ip-du-rpi>`
- **Logs** : `journalctl -u transport-kiosk -f`
- **Arrêt du kiosk** : `sudo systemctl stop transport-kiosk`
- **Désactiver au boot** : `sudo systemctl disable transport-kiosk`
