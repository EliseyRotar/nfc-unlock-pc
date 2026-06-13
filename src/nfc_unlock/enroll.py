"""
Enrollment wizard: scan your phone (or NFC tag) once, store its identifier,
and store your account password in the OS keyring.

Run with:  python src/main.py enroll
"""

import getpass
import platform

from . import config, reader


def main():
    print("=== NFC Unlock PC - Enrollment ===")
    print()
    print("1. Make sure your ACR122U is plugged in.")

    try:
        r = reader.get_reader()
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return

    print(f"   Using reader: {r}")
    print()
    print("2. Present your phone or NFC tag to the reader now...")
    print("   - Phone: open the 'NFC Unlock Companion' app (android-hce-app/) and")
    print("     hold the back of the phone against the reader.")
    print("   - Physical tag/sticker: just place it on the reader.")

    identifier = reader.wait_for_tag(r)
    print(f"   Detected! Identifier = {identifier}")
    print()

    username = input(
        "3. Username to type at the lock screen (Windows SendInput method only - "
        "leave blank to use the currently logged-in user; ignored on Linux): "
    ).strip() or None

    password = getpass.getpass(
        "4. Account password (stored in your OS keyring, never in plain text; "
        "not needed if you only use the Linux PAM method): "
    )

    cfg = config.load_config()
    cfg["uid"] = identifier
    cfg["username"] = username
    if password:
        cfg["password_stored"] = True
        config.set_password(password)
    config.save_config(cfg)

    print()
    print("Saved to config.json" + (" + OS keyring." if password else "."))

    system = platform.system()
    if system == "Windows":
        print("Next: install the background task with scripts\\install_task.ps1 (run as Administrator).")
    elif system == "Linux":
        print("Next, pick one:")
        print("  - No password typing (recommended): sudo bash scripts/setup_pam_linux.sh <pam-service>")
        print("    e.g. 'light-locker', 'swaylock', 'i3lock' - see README for details.")
        print("  - Type the stored password on tap: bash scripts/install_service_linux.sh")
    else:
        print("Next: run 'python src/main.py run' to start the watcher.")


if __name__ == "__main__":
    main()
