#!/usr/bin/env python3
"""
Cross-platform installer for nfc-unlock-pc.

Detects the host OS, installs the system packages needed to talk to the
ACR122U (PC/SC stack) and to simulate keystrokes at the lock screen, then
installs the Python dependencies.

Usage:
    python install.py
"""

import os
import platform
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, check=False)


def pip_install():
    run([sys.executable, "-m", "pip", "install", "-r", os.path.join(ROOT, "requirements.txt")])


def install_linux():
    print("Detected Linux.")

    pkg_managers = {
        "apt": ["sudo", "apt-get", "install", "-y", "pcscd", "pcsc-tools", "libpcsclite-dev",
                "xdotool", "wtype", "python3-venv", "python3-pip"],
        "dnf": ["sudo", "dnf", "install", "-y", "pcsc-lite", "pcsc-tools", "pcsc-lite-devel",
                "xdotool", "wtype", "python3-pip"],
        "pacman": ["sudo", "pacman", "-S", "--needed", "--noconfirm", "pcsclite", "pcsc-tools",
                   "ccid", "xdotool", "wtype", "python-pip"],
        "zypper": ["sudo", "zypper", "install", "-y", "pcsc-lite", "pcsc-tools",
                   "xdotool", "wtype", "python3-pip"],
    }

    for mgr, cmd in pkg_managers.items():
        if shutil.which(mgr):
            print(f"Using package manager: {mgr}")
            run(cmd)
            break
    else:
        print("Could not detect apt/dnf/pacman/zypper.")
        print("Please install manually: pcscd (or pcsc-lite), pcsc-tools, ccid, xdotool and/or wtype.")

    if shutil.which("systemctl"):
        run(["sudo", "systemctl", "enable", "--now", "pcscd"])

    pip_install()

    print()
    print("Next steps:")
    print("  1. python3 src/main.py enroll")
    print("  2. bash scripts/install_service_linux.sh   (installs a systemd --user service)")


def install_windows():
    print("Detected Windows.")
    pip_install()

    print()
    print("Next steps:")
    print("  1. Install the official ACS ACR122U driver:")
    print("     https://www.acs.com.hk/en/driver/3/acr122u-usb-nfc-reader/")
    print("  2. python src\\main.py enroll")
    print("  3. Run scripts\\install_task.ps1 from an elevated PowerShell")


def install_macos():
    print("Detected macOS (best-effort, not officially tested).")
    print("PC/SC is built into macOS, so the ACR122U should work via pyscard out of the box.")
    pip_install()
    print()
    print("Next steps:")
    print("  1. python3 src/main.py enroll")
    print("  2. Wire up src/main.py run via launchd if you'd like it to run at login.")


def main():
    system = platform.system()
    if system == "Linux":
        install_linux()
    elif system == "Windows":
        install_windows()
    elif system == "Darwin":
        install_macos()
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)


if __name__ == "__main__":
    main()
