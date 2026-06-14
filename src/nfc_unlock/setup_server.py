"""
Local setup wizard: a small Flask app, served on localhost only, that walks
you through picking your NFC reader and tapping your phone/tag - instead of
the old `enroll` CLI prompts.

Run with:  python src/main.py setup
(opens http://127.0.0.1:5151 in your default browser automatically)

Nothing here is exposed beyond localhost, and the server exits once setup
is finished (or you close the tab and press Ctrl+C).
"""

import json
import os
import platform
import subprocess
import threading
import time
import webbrowser

from flask import Flask, jsonify, request

from . import config, reader

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

# Common USB vendor IDs for PC/SC NFC / smart-card readers, used only to
# recognize a plugged-in-but-driverless reader so we can offer to fix it.
# ACS (ACR122U, ACR1252U, ...) = 072F, Identiv = 046A, SCM Micro = 04E6.
KNOWN_READER_VIDS = ["VID_072F", "VID_046A", "VID_04E6"]

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/readers")
def api_readers():
    """
    List every PC/SC reader currently plugged in - not just the ACR122U.
    Any PC/SC-compatible reader (ACR122U, ACR1252U, PN532-based USB readers,
    etc.) shows up here and can be used.
    """
    try:
        rs = reader.list_readers()
    except Exception as exc:
        return jsonify({"readers": [], "error": str(exc)})
    return jsonify({"readers": [str(r) for r in rs]})


@app.route("/api/scan")
def api_scan():
    """
    One-shot poll of the reader at the given index for a tag/phone.
    The frontend calls this repeatedly (every ~400ms) while showing
    "place your device on the reader".
    """
    index = request.args.get("reader", type=int)
    try:
        rs = reader.list_readers()
        if index is None or index < 0 or index >= len(rs):
            return jsonify({"error": "Invalid reader index"}), 400
        ident = reader.get_identifier(rs[index])
        return jsonify({"identifier": ident})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/driver_status")
def api_driver_status():
    """
    Best-effort check: do we already have a working PC/SC reader? If not (on
    Windows), is there a plugged-in NFC/smart-card-looking USB device that
    Windows hasn't matched a driver to yet?

    This drives the "Step 0" of the wizard - most users on a modern Windows
    install need nothing here (the inbox CCID driver already handles the
    ACR122U), so this step is skipped entirely when a reader is already
    visible to pyscard.
    """
    try:
        rs = reader.list_readers()
    except Exception:
        rs = []

    result = {"readers_found": len(rs), "system": platform.system(), "candidates": []}
    if rs or platform.system() != "Windows":
        return jsonify(result)

    # No PC/SC reader yet - look for a plugged-in device that looks like an
    # NFC/smart-card reader but has no working driver (Device Manager
    # "problem" status), via PowerShell's Get-PnpDevice.
    try:
        ps_cmd = (
            "Get-PnpDevice | Where-Object { "
            "$_.InstanceId -match 'VID_(072F|046A|04E6)' -or "
            "$_.FriendlyName -match 'ACR1|ACR3|NFC|PC/SC|PCSC|Smart ?Card|Contactless' "
            "} | Select-Object FriendlyName, Status, Class, InstanceId | ConvertTo-Json -Compress"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=20, check=False,
        ).stdout.strip()
        if out:
            devices = json.loads(out)
            if isinstance(devices, dict):
                devices = [devices]
            result["candidates"] = [
                d for d in devices if d.get("Status") != "OK"
            ]
    except Exception as exc:
        result["error"] = str(exc)

    return jsonify(result)


@app.route("/api/install_driver", methods=["POST"])
def api_install_driver():
    """
    Windows only: launch scripts/install_driver_windows.ps1 elevated (UAC
    prompt) to make Windows re-scan for hardware changes and fetch a driver
    for the reader from Windows Update / its driver store.
    """
    if platform.system() != "Windows":
        return jsonify({"error": "Not supported on this platform"}), 400

    script = os.path.join(PROJECT_ROOT, "scripts", "install_driver_windows.ps1")
    try:
        subprocess.Popen([
            "powershell", "-NoProfile", "-Command",
            f"Start-Process powershell -Verb RunAs -ArgumentList "
            f"'-NoProfile -ExecutionPolicy Bypass -File \"{script}\"' -Wait",
        ])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"ok": True})


@app.route("/api/platform")
def api_platform():
    system = platform.system()
    cfg = config.load_config()
    return jsonify({
        "system": system,
        "current_uid": cfg.get("uid"),
        "password_stored": bool(cfg.get("password_stored")),
    })


@app.route("/api/enroll", methods=["POST"])
def api_enroll():
    """
    Save the confirmed identifier (and optional username/password) to
    config.json / the OS keyring. Equivalent to the old enroll.py wizard's
    final step.
    """
    data = request.get_json(force=True) or {}
    identifier = data.get("identifier")
    if not identifier:
        return jsonify({"error": "Missing identifier"}), 400

    username = (data.get("username") or "").strip() or None
    password = data.get("password") or ""

    cfg = config.load_config()
    cfg["uid"] = identifier
    cfg["username"] = username
    if password:
        cfg["password_stored"] = True
        config.set_password(password)
    else:
        cfg["password_stored"] = False
    config.save_config(cfg)

    system = platform.system()
    next_steps = _next_steps(system, bool(password))
    return jsonify({"ok": True, "next_steps": next_steps})


def _next_steps(system, has_password):
    project_root = os.path.abspath(os.path.join(HERE, "..", ".."))
    if system == "Windows":
        return {
            "tier": 2,
            "title": "Windows: install the background unlock task",
            "commands": [
                r"cd scripts",
                r"powershell -ExecutionPolicy Bypass -File .\install_task.ps1   # run as Administrator",
            ],
            "note": "Registers a SYSTEM scheduled task that types your stored "
                    "password at the Winlogon lock screen when you tap.",
        }
    if system == "Linux":
        return {
            "tier": "1 or 2",
            "title": "Linux: choose your unlock method",
            "tier1": {
                "label": "Tier 1 - no password typed (recommended)",
                "commands": [
                    "sudo bash scripts/setup_pam_linux.sh <pam-service>",
                    "# e.g. light-locker, gdm-password, sddm, swaylock, i3lock, hyprlock",
                    "# run 'ls /etc/pam.d/' if you're not sure which one your locker uses",
                ],
            },
            "tier2": {
                "label": "Tier 2 - types your stored password" + ("" if has_password else " (you didn't set a password, so set one by re-running setup first)"),
                "commands": [
                    "bash scripts/install_service_linux.sh",
                ],
            },
            "note": f"Project root: {project_root}",
        }
    return {"tier": None, "title": "Unsupported platform", "commands": [], "note": ""}


def _open_browser():
    time.sleep(0.7)
    webbrowser.open("http://127.0.0.1:5151")


def main():
    threading.Thread(target=_open_browser, daemon=True).start()
    # Bind to localhost only - this is a local setup tool, never expose it.
    app.run(host="127.0.0.1", port=5151, debug=False)


if __name__ == "__main__":
    main()
