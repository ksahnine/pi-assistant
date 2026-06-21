#!/usr/bin/env python3
import RPi.GPIO as GPIO
import json
import time
import requests
import websocket
import signal
import sys
import subprocess
from queue import Queue, Empty

CONFIG_PATH = "/home/pi/transport-display/config.json"
CDP_URL = "http://127.0.0.1:9222/json"

event_queue = Queue()
running = True
display_on = True


def cleanup(*_args):
    global running
    running = False
    GPIO.cleanup()
    sys.exit(0)


signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_ws_url():
    for attempt in range(30):
        try:
            r = requests.get(CDP_URL, timeout=3)
            tabs = r.json()
            if not tabs:
                time.sleep(1)
                continue
            for tab in tabs:
                url = tab.get("url", "")
                if url.startswith("http") and "about:" not in url:
                    return tab["webSocketDebuggerUrl"]
            return tabs[0]["webSocketDebuggerUrl"]
        except requests.ConnectionError:
            time.sleep(1)
    raise RuntimeError("Impossible de contacter Chromium (port 9222)")


def inject_toast(ws, name, duration):
    js = (
        "(function(){"
        "var e=document.getElementById('__transport_toast__');"
        "if(e)e.remove();"
        "var t=document.createElement('div');"
        "t.id='__transport_toast__';"
        "t.textContent=%r;"
        "Object.assign(t.style,{"
        "position:'fixed',bottom:'20px',right:'20px',zIndex:'999999',"
        "background:'rgba(0,0,0,0.85)',color:'white',padding:'12px 24px',"
        "borderRadius:'8px',fontSize:'24px',fontFamily:'sans-serif',"
        "fontWeight:'bold',opacity:'1',transition:'opacity 0.5s ease'"
        "});"
        "document.body.appendChild(t);"
        "setTimeout(function(){t.style.opacity='0';"
        "setTimeout(function(){t.remove()},500);},%d);"
        "})()"
    ) % (name, duration * 1000)
    cmd = json.dumps({"id": 2, "method": "Runtime.evaluate",
                      "params": {"expression": js}})
    ws.send(cmd)


def navigate_to(url, name, duration):
    ws_url = get_ws_url()
    ws = websocket.create_connection(ws_url, timeout=10)

    nav = json.dumps({"id": 1, "method": "Page.navigate",
                      "params": {"url": url}})
    ws.send(nav)

    while True:
        resp = json.loads(ws.recv())
        if resp.get("method") == "Page.frameStoppedLoading":
            break

    inject_toast(ws, name, duration)
    ws.close()


def toggle_display(name, duration):
    global display_on
    display_on = not display_on
    state = "1" if display_on else "0"
    subprocess.run(["vcgencmd", "display_power", state], capture_output=True)
    print("Écran %s" % ("allumé" if display_on else "éteint"))
    if display_on:
        try:
            ws_url = get_ws_url()
            ws = websocket.create_connection(ws_url, timeout=5)
            inject_toast(ws, name, duration)
            ws.close()
        except Exception as e:
            print("Toast écran allumé impossible: %s" % e)


def main():
    config = load_config()
    buttons = config["buttons"]
    power_btn = config.get("power_button")
    duration = config.get("overlay_duration_seconds", 2)

    pin_map = {btn["gpio_pin"]: btn for btn in buttons}
    power_pin = power_btn["gpio_pin"] if power_btn else None

    GPIO.setmode(GPIO.BCM)

    for btn in buttons:
        pin = btn["gpio_pin"]
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(pin, GPIO.FALLING,
                              callback=lambda p: event_queue.put(p),
                              bouncetime=300)

    if power_pin is not None:
        GPIO.setup(power_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(power_pin, GPIO.FALLING,
                              callback=lambda p: event_queue.put(p),
                              bouncetime=500)

    nav_count = len(buttons)
    print("gpio-monitor prêt, %d boutons + power" % nav_count)

    while running:
        try:
            pin = event_queue.get(timeout=1)
        except Empty:
            continue

        if power_pin is not None and pin == power_pin:
            print("Bouton power (pin %d)" % pin)
            try:
                toggle_display(power_btn["name"], duration)
            except Exception as e:
                print("Erreur power: %s" % e)
            continue

        btn = pin_map.get(pin)
        if not btn:
            continue
        print("Bouton %s (pin %d)" % (btn["name"], pin))
        try:
            navigate_to(btn["url"], btn["name"], duration)
        except Exception as e:
            print("Erreur: %s" % e)

    GPIO.cleanup()


if __name__ == "__main__":
    main()
