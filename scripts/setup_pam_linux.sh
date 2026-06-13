#!/usr/bin/env bash
#
# Wire up PASSWORDLESS unlock: PAM itself accepts "the enrolled phone/tag is
# on the reader" as a valid authentication factor for the given service
# (your screen locker's PAM service name).
#
# This is the *recommended* Linux setup - nothing is typed anywhere, ever.
# If the tag isn't present, PAM falls through to your normal password prompt
# exactly as before, so you're never locked out.
#
# Usage:
#   sudo bash scripts/setup_pam_linux.sh <pam-service-name>
#
# Common <pam-service-name> values (check /etc/pam.d/ for what exists on
# your system):
#   light-locker, lightdm, gdm-password, sddm, swaylock, i3lock, hyprlock
#
# Prior art / inspiration: this is the same pattern used by SiRFIDaL
# (Raphael Giraut, GPL-3.0) and pam_nfc - an external pam_exec.so helper
# that decides auth success based on NFC presence.

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "This must be run as root (it edits /etc/pam.d/...). Try: sudo bash $0 <service>" >&2
    exit 1
fi

SERVICE="${1:-}"
if [[ -z "$SERVICE" ]]; then
    echo "Usage: sudo bash $0 <pam-service-name>" >&2
    echo "Available PAM services in /etc/pam.d/:" >&2
    ls /etc/pam.d/ >&2
    exit 1
fi

PAM_FILE="/etc/pam.d/${SERVICE}"
if [[ ! -f "$PAM_FILE" ]]; then
    echo "ERROR: $PAM_FILE does not exist." >&2
    echo "Available PAM services:" >&2
    ls /etc/pam.d/ >&2
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Prefer the project virtualenv if install.py created one.
if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="$(command -v python3)"
fi

CHECK_SCRIPT="$PROJECT_ROOT/scripts/pam_nfc_check.py"
LINE="auth    sufficient    pam_exec.so quiet ${PYTHON} ${CHECK_SCRIPT}"

if grep -qF "$CHECK_SCRIPT" "$PAM_FILE"; then
    echo "nfc-unlock-pc is already wired into $PAM_FILE - nothing to do."
    exit 0
fi

BACKUP="${PAM_FILE}.bak.$(date +%Y%m%d%H%M%S 2>/dev/null || echo orig)"
cp -p "$PAM_FILE" "$BACKUP"
echo "Backed up $PAM_FILE -> $BACKUP"

# Insert as the FIRST line: a 'sufficient' module that succeeds short-circuits
# the rest of the auth stack (your password prompt) when the tag is present,
# and is silently skipped (falls through to pam_unix.so etc.) when it's not.
{
    echo "# --- nfc-unlock-pc: tap enrolled phone/tag to unlock (no password) ---"
    echo "$LINE"
    echo "# --- end nfc-unlock-pc ---"
    cat "$PAM_FILE"
} > "${PAM_FILE}.new"
mv "${PAM_FILE}.new" "$PAM_FILE"

echo "Done. $SERVICE now accepts your enrolled NFC phone/tag as an unlock factor."
echo "Your normal password still works as a fallback."
echo
echo "To undo: sudo cp $BACKUP $PAM_FILE"
