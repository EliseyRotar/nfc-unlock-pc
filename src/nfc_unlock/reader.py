"""
ACR122U / PC-SC card reader interface.

The ACR122U exposes itself to Windows as a standard PC/SC smart-card reader,
so we talk to it with `pyscard` (which wraps the Windows WinSCard API) - no
vendor SDK required.

To get the UID of whatever tag is currently on the reader we send the
pseudo-APDU `FF CA 00 00 00` ("Get Data" - UID), which is supported by the
ACR122U's firmware for MIFARE / NTAG / ISO14443-A tags - exactly the kind of
tag you'd stick on the back of a phone (or that some phones can emulate via
NFC tag-writer apps).
"""

import time

from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.Exceptions import NoCardException, CardConnectionException

GET_UID_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]


def list_readers():
    """Return the list of available PC/SC readers."""
    return readers()


def get_reader():
    """Return the ACR122U reader, or the first available reader."""
    rs = list_readers()
    if not rs:
        raise RuntimeError(
            "No PC/SC readers found. Make sure the ACR122U is plugged in, "
            "the official ACS driver is installed, and the Windows "
            "'Smart Card' service is running."
        )
    for r in rs:
        if "ACR122" in str(r) or "ACR 122" in str(r):
            return r
    return rs[0]


def get_uid(reader):
    """
    Return the UID (as an uppercase hex string, no spaces) of the tag
    currently on `reader`, or None if no tag is present.
    """
    try:
        connection = reader.createConnection()
        connection.connect()
        data, sw1, sw2 = connection.transmit(GET_UID_APDU)
        if sw1 == 0x90:
            return toHexString(data).replace(" ", "").upper()
        return None
    except (NoCardException, CardConnectionException):
        return None
    except Exception:
        # Reader hiccups (e.g. card pulled away mid-transaction) - treat as "no tag"
        return None


def wait_for_tag(reader=None, poll_interval=0.25):
    """Block until a tag is placed on the reader, then return its UID."""
    reader = reader or get_reader()
    while True:
        uid = get_uid(reader)
        if uid:
            return uid
        time.sleep(poll_interval)


def poll(callback, reader=None, interval=0.4):
    """
    Continuously poll `reader`, calling `callback(uid)` once each time a
    *new* tag is presented (i.e. it won't fire repeatedly while the tag
    just sits on the reader).
    """
    reader = reader or get_reader()
    last_uid = None
    while True:
        uid = get_uid(reader)
        if uid and uid != last_uid:
            callback(uid)
        last_uid = uid
        time.sleep(interval)
