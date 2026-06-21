#!/usr/bin/env python3
import RPi.GPIO as GPIO
import signal
import sys
import json

CONFIG_PATH = "/home/pi/transport-display/config.json"


def cleanup(*_a):
    GPIO.cleanup()
    print("\nFin.")
    sys.exit(0)


def main():
    pins = []

    if len(sys.argv) > 1:
        pins = [int(sys.argv[1])]
    else:
        try:
            cfg = json.load(open(CONFIG_PATH))
            for p in cfg.get("input", {}).get("gpio", {}).get("pins", []):
                pins.append(p["gpio_pin"])
        except Exception:
            pass
        if not pins:
            print("Usage: %s [pin_gpio]" % sys.argv[0])
            sys.exit(1)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    GPIO.setmode(GPIO.BCM)
    for pin in pins:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(pin, GPIO.FALLING,
                              callback=lambda c: print("  GPIO %2d  presse" % c),
                              bouncetime=300)

    print("Test boutons GPIO : pins %s" % pins)
    print("Appuyez sur les boutons. Ctrl+C pour quitter.\n")

    signal.pause()


if __name__ == "__main__":
    main()
