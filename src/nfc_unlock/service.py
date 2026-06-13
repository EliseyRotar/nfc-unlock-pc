"""
Background service loop (Tier 2): watches the ACR122U for the enrolled
phone/tag and types the stored password to unlock the workstation.

This is NOT used by Linux Tier 1 (PAM, no typing) - that path runs
scripts/pam_nfc_check.py directly via pam_exec.so and never starts this
service. Run this only for Windows, or for Linux Tier 2
(scripts/install_service_linux.sh).

Run with:  python src\\main.py run    (or as the SYSTEM scheduled task,
                                         see scripts/install_task.ps1)
"""

import time

from . import config, reader, unlocker


def main():
    cfg = config.load_config()

    if not cfg.get("uid"):
        print("No phone/tag enrolled yet. Run 'python src/main.py enroll' first.")
        return

    if not cfg.get("password_stored"):
        print(
            "No password stored - this enrollment looks like a Linux Tier 1 "
            "(PAM-only) setup. Nothing to do here; this watcher is only for "
            "Tier 2 (typed-password) setups. See scripts/setup_pam_linux.sh."
        )
        return

    print("NFC Unlock service running. Waiting for phone/tag taps on the ACR122U...")

    def on_tag(identifier):
        timestamp = time.strftime("%H:%M:%S")
        if identifier == cfg["uid"]:
            print(f"[{timestamp}] Authorized phone/tag {identifier} detected -> unlocking")
            try:
                password = config.get_password()
                unlocker.unlock_with_password(cfg.get("username"), password)
            except Exception as exc:
                print(f"[{timestamp}] Unlock failed: {exc}")
        else:
            print(f"[{timestamp}] Unrecognized identifier: {identifier}")

    while True:
        try:
            reader.poll(on_tag)
        except RuntimeError as exc:
            # Reader unplugged / not found - keep retrying
            print(f"Reader error: {exc}. Retrying in 5s...")
            time.sleep(5)


if __name__ == "__main__":
    main()
