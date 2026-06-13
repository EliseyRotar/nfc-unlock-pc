"""
Linux: types your password into the screen locker using virtual input.

Unlike Windows, Linux screen lockers (i3lock, light-locker, xscreensaver,
swaylock, hyprlock, ...) normally run *inside your own user session*, so a
regular user process can send them input directly - no root/SYSTEM needed.
This service is meant to run as a `systemd --user` service
(see scripts/install_service_linux.sh).

- X11: uses `xdotool` to type text and press Return.
- Wayland (wlroots-based compositors: Sway, Hyprland, ...): uses `wtype`,
  which talks to the compositor's virtual-keyboard protocol.

Install the required tool with your package manager, e.g.:
    sudo apt install xdotool       # X11
    sudo pacman -S wtype           # Wayland / wlroots
"""

import os
import shutil
import subprocess
import time


def _is_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def _run(cmd):
    subprocess.run(cmd, check=False)


def type_text(text: str):
    if _is_wayland():
        if shutil.which("wtype"):
            _run(["wtype", text])
            return
        raise RuntimeError(
            "wtype not found. Install it for Wayland support "
            "(e.g. 'sudo pacman -S wtype' or 'sudo apt install wtype')."
        )

    if shutil.which("xdotool"):
        _run(["xdotool", "type", "--clearmodifiers", "--delay", "20", text])
        return
    raise RuntimeError(
        "xdotool not found. Install it for X11 support "
        "(e.g. 'sudo apt install xdotool' or 'sudo pacman -S xdotool')."
    )


def press_enter():
    if _is_wayland():
        if shutil.which("wtype"):
            _run(["wtype", "-k", "Return"])
            return
    if shutil.which("xdotool"):
        _run(["xdotool", "key", "Return"])


def wake_display():
    """Best-effort: nudge input so the screen turns back on."""
    if _is_wayland():
        return  # most Wayland compositors wake on any input event sent below
    if shutil.which("xdotool"):
        _run(["xdotool", "key", "shift"])


def unlock_with_password(username, password: str):
    """
    Wake the screen and type the password + Enter into the active locker.

    `username` is accepted for API symmetry with the Windows implementation
    but is normally unused on Linux, since the lock screen is already tied
    to your logged-in session and only asks for the password.
    """
    wake_display()
    time.sleep(1.0)
    type_text(password)
    press_enter()
