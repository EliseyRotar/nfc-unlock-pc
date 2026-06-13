"""
Entry point.

Usage:
    python src\\main.py            - run the unlock service (default)
    python src\\main.py enroll     - enroll a new NFC tag + password
    python src\\main.py list       - list connected PC/SC readers
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from nfc_unlock import enroll, service, reader  # noqa: E402


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"

    if cmd == "enroll":
        enroll.main()
    elif cmd == "list":
        for r in reader.list_readers():
            print(r)
    elif cmd == "run":
        service.main()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
