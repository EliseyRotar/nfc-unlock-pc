"""
Background service loop: watches the ACR122U for the enrolled tag and
unlocks the workstation when it's presented.

Run with:  python src\\main.py        (or as the SYSTEM scheduled task,
                                         see scripts/install_task.ps1)
"""

import time

from . import config, reader, unlocker


def main():
    cfg = config.load_config()

    if not cfg.get("uid") or not cfg.get("password_stored"):
        print("No tag enrolled yet. Run 'python src/main.py enroll' first.")
        return

    print("NFC Unlock service running. Waiting for tag taps on the ACR122U...")

    def on_tag(uid):
        timestamp = time.strftime("%H:%M:%S")
        if uid == cfg["uid"]:
            print(f"[{timestamp}] Authorized tag {uid} detected -> unlocking")
            try:
                password = config.get_password()
                unlocker.unlock_with_password(cfg.get("username"), password)
            except Exception as exc:
                print(f"[{timestamp}] Unlock failed: {exc}")
        else:
            print(f"[{timestamp}] Unrecognized tag: {uid}")

    while True:
        try:
            reader.poll(on_tag)
        except RuntimeError as exc:
            # Reader unplugged / not found - keep retrying
            print(f"Reader error: {exc}. Retrying in 5s...")
            time.sleep(5)


if __name__ == "__main__":
    main()
