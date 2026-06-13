"""
Enrollment wizard: scan your phone's NFC tag once, store its UID, and store
your Windows password encrypted with DPAPI.

Run with:  python src\\main.py enroll
"""

import getpass

from . import config, reader


def main():
    print("=== NFC Unlock for Windows - Enrollment ===")
    print()
    print("1. Make sure your ACR122U is plugged in.")

    try:
        r = reader.get_reader()
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return

    print(f"   Using reader: {r}")
    print()
    print("2. Place your phone (with its NFC tag/sticker) on the reader now...")

    uid = reader.wait_for_tag(r)
    print(f"   Tag detected! UID = {uid}")
    print()

    username = input(
        "3. Username to type at the lock screen (Windows only - leave blank "
        "to use the currently logged-in user; ignored on Linux): "
    ).strip() or None

    password = getpass.getpass(
        "4. Account password (stored in your OS keyring, never in plain text): "
    )

    cfg = config.load_config()
    cfg["uid"] = uid
    cfg["username"] = username
    cfg["password_stored"] = True
    config.set_password(password)
    config.save_config(cfg)

    print()
    print("Saved to config.json + OS keyring.")
    import platform
    if platform.system() == "Windows":
        print("Next: install the background task with scripts\\install_task.ps1 (run as Administrator).")
    elif platform.system() == "Linux":
        print("Next: install the background service with scripts/install_service_linux.sh")
    else:
        print("Next: run 'python src/main.py run' to start the watcher.")


if __name__ == "__main__":
    main()
