"""
ACR122U / PC-SC card reader interface.

The ACR122U exposes itself as a standard PC/SC smart-card reader on both
Windows and Linux, so we talk to it with `pyscard` - no vendor SDK required.

Two kinds of "tag" are supported:

1. Physical NFC tags/stickers (NTAG21x, MIFARE, ...). We read their UID with
   the pseudo-APDU `FF CA 00 00 00` ("Get Data" - UID).

2. A phone running the nfc-unlock-pc Android companion app (see
   android-hce-app/), which uses Host Card Emulation (HCE) to present a
   custom AID and return a fixed secret token. Physical-tag UIDs are
   trivially clonable and HCE UIDs are randomized by Android for privacy, so
   for phones we SELECT our own AID (`F0AC1DC0DE0001`) and use the token the
   app returns as the identifier instead of any UID.

`get_identifier()` tries both and returns whichever responds.
"""

import time

from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.Exceptions import NoCardException, CardConnectionException

GET_UID_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]

# Must match res/xml/apduservice.xml in android-hce-app/
HCE_AID_HEX = "F0AC1DC0DE0001"
SELECT_APDU_PREFIX = [0x00, 0xA4, 0x04, 0x00]


def _hex_to_bytes(hexstr):
    return [int(hexstr[i:i + 2], 16) for i in range(0, len(hexstr), 2)]


def list_readers():
    """Return the list of available PC/SC readers."""
    return readers()


def get_reader():
    """Return the ACR122U reader, or the first available reader."""
    rs = list_readers()
    if not rs:
        raise RuntimeError(
            "No PC/SC readers found. Make sure the ACR122U is plugged in, "
            "the driver is installed (Windows), and the smart card service "
            "is running (Windows: 'Smart Card' service / Linux: pcscd)."
        )
    for r in rs:
        if "ACR122" in str(r) or "ACR 122" in str(r):
            return r
    return rs[0]


def get_uid(reader):
    """
    Return the UID (as an uppercase hex string, no spaces) of the physical
    tag currently on `reader`, or None if no tag is present.
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


def get_hce_token(reader, aid_hex=HCE_AID_HEX):
    """
    SELECT the nfc-unlock-pc AID and return the token reported by the
    Android companion app, or None if nothing answers for that AID.
    """
    try:
        connection = reader.createConnection()
        connection.connect()
        aid = _hex_to_bytes(aid_hex)
        apdu = SELECT_APDU_PREFIX + [len(aid)] + aid + [0x00]
        data, sw1, sw2 = connection.transmit(apdu)
        if sw1 == 0x90 and sw2 == 0x00 and data:
            return toHexString(data).replace(" ", "").upper()
        return None
    except (NoCardException, CardConnectionException):
        return None
    except Exception:
        return None


def get_identifier(reader):
    """
    Return a stable identifier for whatever is on the reader right now:
    a physical tag's UID, or an HCE phone's token. None if nothing usable
    is present.
    """
    uid = get_uid(reader)
    if uid:
        return uid
    return get_hce_token(reader)


def wait_for_tag(reader=None, poll_interval=0.25):
    """Block until a tag/phone is placed on the reader, then return its identifier."""
    reader = reader or get_reader()
    while True:
        ident = get_identifier(reader)
        if ident:
            return ident
        time.sleep(poll_interval)


def poll(callback, reader=None, interval=0.4):
    """
    Continuously poll `reader`, calling `callback(identifier)` once each
    time a *new* tag/phone is presented (i.e. it won't fire repeatedly while
    it just sits on the reader).
    """
    reader = reader or get_reader()
    last_id = None
    while True:
        ident = get_identifier(reader)
        if ident and ident != last_id:
            callback(ident)
        last_id = ident
        time.sleep(interval)
