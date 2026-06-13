"""
Windows: wakes the display and types your credentials at the lock screen.

The Windows lock screen (LogonUI) runs on the secure "Winlogon" desktop,
which is isolated from the interactive desktop for security reasons. A
normal user-mode process CANNOT send keystrokes to it. The only practical
way around this without writing a full custom Credential Provider (a signed
COM/C++ component) is to run this code as the SYSTEM account via a Scheduled
Task ("Run whether user is logged on or not"). SYSTEM is allowed to attach to
the Winlogon desktop with OpenDesktop/SetThreadDesktop and inject input with
SendInput.

This is the same technique used by several open-source "tap to unlock"
hobby projects. See README.md for the security caveats and for the
alternative (Rohos Logon Key, a ready-made commercial product with native
NFC/RFID support).
"""

import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002

DESKTOP_GENERIC_ALL = 0x10000000

VK_RETURN = 0x0D
VK_TAB = 0x09

PUL = ctypes.POINTER(ctypes.c_ulong)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _InputUnion)]


def _send_input(ki: KEYBDINPUT):
    inp = INPUT(INPUT_KEYBOARD, _InputUnion(ki=ki))
    user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))


def _key_extra():
    return ctypes.pointer(ctypes.c_ulong(0))


def _send_unicode_char(ch, keyup=False):
    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if keyup else 0)
    _send_input(KEYBDINPUT(0, ord(ch), flags, 0, _key_extra()))


def _send_vk(vk, keyup=False):
    flags = KEYEVENTF_KEYUP if keyup else 0
    _send_input(KEYBDINPUT(vk, 0, flags, 0, _key_extra()))


def type_text(text: str, delay: float = 0.02):
    for ch in text:
        _send_unicode_char(ch)
        _send_unicode_char(ch, keyup=True)
        time.sleep(delay)


def press_key(vk: int, delay: float = 0.05):
    _send_vk(vk)
    time.sleep(0.02)
    _send_vk(vk, keyup=True)
    time.sleep(delay)


def wake_display():
    """Send a fake mouse move + monitor-on signal so the lock screen is visible."""
    HWND_BROADCAST = 0xFFFF
    WM_SYSCOMMAND = 0x0112
    SC_MONITORPOWER = 0xF170
    user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, -1)
    # Nudge the mouse 1px so Windows registers user activity
    user32.mouse_event(0x0001, 1, 0, 0, 0)
    user32.mouse_event(0x0001, -1, 0, 0, 0)


def switch_to_winlogon_desktop():
    """
    Attach the current thread to the secure 'Winlogon' desktop. Only succeeds
    when this process is running as SYSTEM (e.g. via the Scheduled Task
    installed by scripts/install_task.ps1).
    """
    hdesk = user32.OpenDesktopW("Winlogon", 0, False, DESKTOP_GENERIC_ALL)
    if not hdesk:
        raise OSError(
            "OpenDesktop('Winlogon') failed (error %d). "
            "This process must run as SYSTEM - install it via "
            "scripts/install_task.ps1." % ctypes.get_last_error()
        )
    if not user32.SetThreadDesktop(hdesk):
        raise OSError("SetThreadDesktop failed (error %d)" % ctypes.get_last_error())


def unlock_with_password(username, password: str):
    """
    Wake the screen, attach to the Winlogon desktop and type the username
    (if a password-only field isn't already focused) + password + Enter.
    """
    wake_display()
    time.sleep(1.0)
    switch_to_winlogon_desktop()
    time.sleep(0.5)

    if username:
        type_text(username)
        press_key(VK_TAB)

    type_text(password)
    press_key(VK_RETURN)
