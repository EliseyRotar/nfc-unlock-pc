#!/usr/bin/env python3
"""
PAM helper for nfc-unlock-pc.

Exit code 0  -> the enrolled tag/phone is currently on the ACR122U: PAM
                treats this module as a successful auth factor.
Exit code 1  -> not present (or timed out): PAM falls through to the next
                module (normally pam_unix.so, i.e. your regular password).

Wired up via pam_exec.so as a 'sufficient' step - see
scripts/setup_pam_linux.sh. This is the "no typing" unlock path: PAM itself
authenticates the session, nothing is typed anywhere.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from nfc_unlock import config, reader  # noqa: E402

TIMEOUT_SECONDS = 5
POLL_INTERVAL = 0.3


def main():
    cfg = config.load_config()
    enrolled = cfg.get("uid")
    if not enrolled:
        return 1

    try:
        r = reader.get_reader()
    except RuntimeError:
        return 1

    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        ident = reader.get_identifier(r)
        if ident and ident == enrolled:
            return 0
        time.sleep(POLL_INTERVAL)

    return 1


if __name__ == "__main__":
    sys.exit(main())
