#!/usr/bin/env python3
import json
import time
import subprocess
import signal
import sys
import threading
import requests
import websocket
from queue import Queue, Empty

CONFIG_PATH = "/home/pi/transport-display/config.json"
CDP_URL = "http://127.0.0.1:9222/json"
BACKLIGHT = "/sys/class/backlight/10-0045/bl_power"

event_queue = Queue()
running = True
display_on = True
last_activity = 0.0


def cleanup(*_a):
    global running
    running = False
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


def show_toast(text, duration):
    try:
        ws_url = get_ws_url()
        ws = websocket.create_connection(ws_url, timeout=5)
        inject_toast(ws, text, duration)
        ws.close()
    except Exception as e:
        print("Toast impossible: %s" % e)


def set_backlight(on):
    v = "0" if on else "4"
    try:
        with open(BACKLIGHT, "w") as f:
            f.write(v)
    except PermissionError:
        subprocess.run(["sudo", "tee", BACKLIGHT], input=v,
                       text=True, capture_output=True)


def wake_screen():
    global display_on
    if not display_on:
        display_on = True
        set_backlight(True)
        show_toast("Écran réactivé", 1.5)
        print("Écran ON (réveil)")


def activity():
    global last_activity
    last_activity = time.time()


def setup_ir(ir_cfg):
    import evdev
    from evdev import InputDevice, ecodes
    devices = [InputDevice(p) for p in evdev.list_devices()]
    ir_dev = None
    for d in devices:
        if "ir" in d.name.lower():
            ir_dev = d
            break
    if ir_dev is None:
        print("IR non trouvé")
        return
    print("IR: %s sur %s" % (ir_dev.name, ir_dev.path))
    keymap = ir_cfg["keymap"]

    def loop():
        for event in ir_dev.read_loop():
            if event.type == ecodes.EV_KEY and event.value == 1:
                key_name = ecodes.KEY.get(event.code)
                if not key_name:
                    continue
                activity()
                if not display_on:
                    wake_screen()
                mapping = keymap.get(key_name)
                if mapping:
                    event_queue.put(mapping)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


def setup_touch():
    import evdev
    from evdev import InputDevice, ecodes
    devices = [InputDevice(p) for p in evdev.list_devices()]
    touch_dev = None
    for d in devices:
        name = d.name.lower()
        if "ft5" in name or "touch" in name:
            touch_dev = d
            break
    if touch_dev is None:
        print("Touch non trouvé")
        return
    print("Touch: %s sur %s" % (touch_dev.name, touch_dev.path))

    def loop():
        for event in touch_dev.read_loop():
            if (event.type == ecodes.EV_KEY and
                event.code == ecodes.BTN_TOUCH and
                    event.value == 1):
                activity()
                if not display_on:
                    wake_screen()

    t = threading.Thread(target=loop, daemon=True)
    t.start()


def main():
    global display_on, last_activity
    config = load_config()
    screens = config["screens"]
    default_screen = config.get("default_screen", 0)
    power_cfg = config.get("power", {})
    power_name = power_cfg.get("name", "Veille")
    idle_sleep = power_cfg.get("idle_sleep_seconds", 0)
    duration = config.get("display", {}).get("overlay_duration_seconds", 2)

    if not screens:
        sys.exit("Aucun écran configuré")

    try:
        with open(BACKLIGHT) as f:
            display_on = f.read().strip() == "0"
    except Exception:
        pass

    last_activity = time.time()

    setup_ir(config["ir"])
    setup_touch()
    print("gpio-monitor prêt, %d écrans" % len(screens))

    while running:
        try:
            ev = event_queue.get(timeout=1)
        except Empty:
            if (idle_sleep > 0 and display_on and
                    time.time() - last_activity >= idle_sleep):
                print("Veille automatique")
                display_on = False
                set_backlight(False)
            continue

        action = ev.get("action")
        if action == "navigate":
            idx = ev.get("screen", default_screen)
            if idx < 0 or idx >= len(screens):
                print("Index invalide: %d" % idx)
                continue
            s = screens[idx]
            print("Navigation: %s" % s["name"])
            navigate_to(s["url"], s["name"], duration)
        elif action == "power":
            if display_on:
                display_on = False
                set_backlight(False)
                print("Écran OFF")
            else:
                wake_screen()
                print("Écran ON (power)")


if __name__ == "__main__":
    main()
