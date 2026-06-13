"""
Cross-platform configuration storage for nfc-unlock-pc.

The enrolled tag UID and username live in config.json (git-ignored). The
account password is stored in the operating system's native secure
credential store via the `keyring` library, never in plain text and never
in config.json:

  - Windows -> Credential Manager (DPAPI-backed)
  - Linux   -> Secret Service (GNOME Keyring / KWallet)
  - macOS   -> Keychain
"""

import json
import os

import keyring

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config.json")

KEYRING_SERVICE = "nfc-unlock-pc"
KEYRING_USERNAME = "login-password"

DEFAULT_CONFIG = {
    "uid": None,            # enrolled identifier (hex string): physical tag UID or phone HCE token
    "username": None,       # account username to type at the lock screen (Windows; unused on Linux)
    "password_stored": False,
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    return merged


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def set_password(password: str):
    """Store the account password in the OS-native secure credential store."""
    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, password)


def get_password() -> str:
    """Retrieve the account password from the OS-native secure credential store."""
    pwd = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    if pwd is None:
        raise RuntimeError("No password stored in the OS keyring - run 'enroll' again.")
    return pwd
