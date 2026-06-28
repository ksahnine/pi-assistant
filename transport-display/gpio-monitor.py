#!/usr/bin/env python3
import json
import time
import subprocess
import signal
import sys
import requests
import websocket
import threading
from queue import Queue, Empty

CONFIG_PATH = "/home/pi/transport-display/config.json"
CDP_URL = "http://127.0.0.1:9222/json"

event_queue = Queue()
running = True
display_on = True


def cleanup(*_a):
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
    print("Écran %s" % ("ON" if display_on else "OFF"))
    if display_on:
        try:
            ws_url = get_ws_url()
            ws = websocket.create_connection(ws_url, timeout=5)
            inject_toast(ws, name, duration)
            ws.close()
        except Exception as e:
            print("Toast écran ON impossible: %s" % e)


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
        print("Périphérique IR non trouvé")
        sys.exit(1)

    print("IR: %s sur %s" % (ir_dev.name, ir_dev.path))
    keymap = ir_cfg["keymap"]

    def read_loop():
        for event in ir_dev.read_loop():
            if event.type == ecodes.EV_KEY and event.value == 1:
                key_name = ecodes.KEY.get(event.code)
                mapping = keymap.get(key_name) if key_name else None
                if mapping:
                    event_queue.put(mapping)

    t = threading.Thread(target=read_loop, daemon=True)
    t.start()


def main():
    config = load_config()
    screens = config["screens"]
    default_screen = config.get("default_screen", 0)
    power_name = config.get("power", {}).get("name", "Veille")
    duration = config.get("display", {}).get("overlay_duration_seconds", 2)

    if not screens:
        sys.exit("Aucun écran configuré")

    setup_ir(config["ir"])
    print("gpio-monitor prêt, %d écrans" % len(screens))

    while running:
        try:
            ev = event_queue.get(timeout=1)
        except Empty:
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
            toggle_display(power_name, duration)


if __name__ == "__main__":
    main()
