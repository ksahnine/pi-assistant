#!/usr/bin/env python3
import evdev
import sys
import signal

def find_ir_device():
    devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
    for d in devices:
        if "ir" in d.name.lower():
            return d
    return None

def main():
    dev = find_ir_device()
    if dev is None:
        print("Aucun périphérique IR trouvé.")
        print("Périphériques détectés :")
        for d in [evdev.InputDevice(p) for p in evdev.list_devices()]:
            print("  %-20s %s" % (d.name, d.path))
        sys.exit(1)

    print("Périphérique IR : %s (%s)" % (dev.name, dev.path))
    print("Appuyez sur les touches de la télécommande.")
    print("Ctrl+C pour quitter.\n")

    keys_pressed = {}

    def cleanup(*_a):
        print("\nFin.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)

    for event in dev.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            if event.value == 1:  # press
                try:
                    key_name = evdev.ecodes.KEY[event.code]
                except KeyError:
                    key_name = "KEY_UNKNOWN_%d" % event.code
                if key_name not in keys_pressed:
                    keys_pressed[key_name] = 0
                keys_pressed[key_name] += 1
                count = keys_pressed[key_name]
                print("  %-16s  (scancode %3d)  press #%d" % (key_name, event.code, count))
            elif event.value == 0:  # release
                pass

if __name__ == "__main__":
    main()
