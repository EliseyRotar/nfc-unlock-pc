"""
Platform dispatcher: picks the right `unlock_with_password` implementation.

  - Windows -> unlocker_windows (SendInput to the Winlogon secure desktop,
               must run as SYSTEM via scripts/install_task.ps1)
  - Linux   -> unlocker_linux (xdotool/wtype, runs as your own user via
               scripts/install_service_linux.sh)
"""

import platform

_SYSTEM = platform.system()

if _SYSTEM == "Windows":
    from .unlocker_windows import unlock_with_password
elif _SYSTEM == "Linux":
    from .unlocker_linux import unlock_with_password
else:
    def unlock_with_password(username, password):
        raise NotImplementedError(f"nfc-unlock-pc does not support '{_SYSTEM}' yet")


__all__ = ["unlock_with_password"]
