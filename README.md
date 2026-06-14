# NFC Unlock PC

Tap your **phone** (no sticker, no extra hardware) on a USB **ACR122U NFC
reader** and your **PC unlocks** — Windows or Linux.

This started as "stick an NFC tag on your phone." It isn't that anymore:
every phone made in the last decade already has an NFC radio, and Android
can emulate a card with it (Host Card Emulation / HCE). So the phone *is*
the tag — a small companion app (`android-hce-app/`) makes it answer the
reader with a private token, the same way a physical tag answers with its
UID.

There are two fundamentally different ways this project can unlock your
session, and which one applies depends on your OS:

| | Linux | Windows |
|---|---|---|
| **Tier 1 — no password typed at all** | ✅ via a PAM module (`pam_exec.so`) | ❌ not implemented (see [Roadmap](#roadmap)) |
| **Tier 2 — stored password is typed for you** | ✅ via `xdotool`/`wtype` + systemd | ✅ via `SendInput` to the Winlogon secure desktop |

If you're on Linux, **use Tier 1**. It's not "type the password faster" — PAM
itself accepts "the enrolled phone is on the reader" as a valid login factor,
the same mechanism `pam_exec.so` is designed for. Nothing is stored that
could be typed wrong, leaked via a keylogger, or briefly flash on screen.

If you're on Windows, Tier 2 (typing the stored password into Winlogon) is
currently the only option — see the roadmap for why.

---

## How it works

### The "tag": physical NFC sticker *or* your phone via HCE

```
 ┌────────────────────┐        tap         ┌────────────┐   PC/SC (pyscard)   ┌───────────────────┐
 │ Phone running the   │ ──────────────────▶│  ACR122U   │ ───────────────────▶│ nfc-unlock-pc      │
 │ HCE companion app   │   SELECT AID        │  USB reader│   identifier        │ enroll / service   │
 │ (or a physical tag) │   F0AC1DC0DE0001    └────────────┘                     └─────────┬──────────┘
 └────────────────────┘                                                                   │
                                                                  identifier == enrolled?  │
                                                       ┌───────────────────────────────────┴───────────────────────────────────┐
                                                       ▼                                                                         ▼
                                          Linux Tier 1 (recommended)                                       Linux Tier 2 / Windows (typing)
                                  pam_exec.so → PAM accepts this as auth                         xdotool/wtype (Linux) or SendInput→Winlogon (Windows)
                                  → screen unlocks, NOTHING typed                                → stored password typed + Enter
```

* The ACR122U is a standard **PC/SC smart-card reader** on both Windows and
  Linux — `pyscard` talks to it, no vendor SDK needed.
* For **physical tags** (NTAG21x/MIFARE stickers) we read the UID with the
  `FF CA 00 00 00` "Get UID" APDU.
* For **phones**, Android randomizes the HCE "card UID" on every tap for
  privacy, so a UID check doesn't work. Instead the companion app
  (`android-hce-app/`) registers a proprietary AID (`F0AC1DC0DE0001`) and,
  when that AID is `SELECT`ed, returns a fixed 16-byte token generated on
  first launch. `reader.get_identifier()` tries a UID read first, then falls
  back to selecting that AID — so the rest of the codebase doesn't care
  whether you tapped a sticker or a phone.

### Linux Tier 1 — PAM, no typing

`scripts/setup_pam_linux.sh <pam-service>` inserts one line at the top of
`/etc/pam.d/<service>`:

```
auth sufficient pam_exec.so quiet /path/to/.venv/bin/python /path/to/scripts/pam_nfc_check.py
```

`pam_exec.so` runs `pam_nfc_check.py`, which polls the reader for up to 5
seconds and exits `0` if the enrolled identifier shows up, `1` otherwise.
`sufficient` means: exit 0 → this auth stack succeeds immediately (no
password prompt needed); exit 1 (or no tap within 5s) → PAM falls through to
the next module — your normal `pam_unix.so` password check — completely
unaffected. **You can never be locked out by this**: worst case, it behaves
exactly like the PAM stack did before you ran the script.

This is the same approach used by prior art like
[SiRFIDaL](https://github.com/jpetazzo/sirfidal) (Raphael Giraut, GPL-3.0)
and `pam_nfc` — an external helper deciding PAM auth success based on NFC
presence, rather than a custom PAM module needing to be compiled.

`<pam-service>` is whatever your screen locker registers in `/etc/pam.d/` —
common ones: `light-locker`, `lightdm`, `gdm-password`, `sddm`, `swaylock`,
`i3lock`, `hyprlock`. Check `ls /etc/pam.d/` if unsure.

### Linux Tier 2 / Windows — typing the stored password

Your account password is stored in the **OS-native secure credential store**
via [`keyring`](https://pypi.org/project/keyring/) (Windows Credential
Manager / Linux Secret Service or KWallet) — never in plain text, never in
`config.json`.

* **Windows**: the lock screen runs on an isolated "Winlogon" secure desktop
  that ordinary processes can't send input to. `scripts/install_task.ps1`
  registers the service as a Scheduled Task running as **SYSTEM**, which
  *can* `OpenDesktop("Winlogon")` / `SetThreadDesktop` and then `SendInput`.
* **Linux (Tier 2)**: screen lockers run inside *your* session, so a
  `systemd --user` service (`scripts/install_service_linux.sh`) can type into
  them directly via `xdotool` (X11) or `wtype` (Wayland/wlroots) — no root
  needed. Prefer Tier 1 if your locker's PAM service is reachable; this is
  the fallback for lockers that don't go through PAM at all, or if you'd
  rather not edit `/etc/pam.d/`.

If you'd rather use a polished commercial tool for Windows with native
ACR122U + MIFARE credential-provider integration, see
[Rohos Logon Key](https://rohos.com/) — the most mature existing solution
found during research, and the closest thing Windows has to Linux's PAM
Tier 1.

---

## Hardware / prerequisites

1. **ACR122U USB NFC reader** (or compatible clone).
2. **A phone with NFC** (Android 5.0+, the vast majority of phones since
   ~2015) running the companion app — *or*, if you'd rather not install
   anything on your phone, an NTAG213/215/216 or MIFARE Classic sticker.
3. Windows 10/11, or Linux (any PAM-based login/lock screen for Tier 1; X11
   or a wlroots Wayland compositor for the Tier 2 `wtype` path).
4. [Python 3.10+](https://www.python.org/downloads/) on PATH (3.9–3.13 if
   you hit the `pyscard` build issue below — `install.py` handles this).

---

## Quick start (all platforms)

```bash
git clone https://github.com/EliseyRotar/nfc-unlock-pc.git
cd nfc-unlock-pc
python install.py
```

`install.py` detects your OS and:

- **Linux**: installs `pcscd`/`pcsc-lite`, `pcsc-tools`, `xdotool`, `wtype`
  via your distro's package manager (apt/dnf/pacman/zypper), enables the
  `pcscd` service, then installs the Python requirements.
- **Windows**: installs the Python requirements (falling back to a `.venv`
  with an older Python if your default Python has no prebuilt `pyscard`
  wheel — see [Troubleshooting](#troubleshooting)). Most readers (including
  the ACR122U) work with Windows' inbox CCID smart-card driver with zero
  extra steps; if the setup wizard's first step doesn't see your reader, it
  offers to let Windows search for a driver for it automatically (see below).
- **macOS**: installs the Python requirements (PC/SC is built in).

### 1. Get the companion app on your phone

Build `android-hce-app/` in Android Studio and install it on your phone (see
`android-hce-app/README.md`), or write an NTAG sticker if you're going the
physical-tag route instead.

### 2. Enroll

```bash
python src/main.py setup
```

This opens a setup wizard in your browser (served locally, never exposed off
your machine). First, on Windows, it checks whether your reader is already
working - if not, and it spots a plugged-in NFC/smart-card device Windows
hasn't matched a driver to yet, it offers a one-click "let Windows find a
driver" (a permission-prompted re-scan against Windows Update/driver store -
this is how the inbox CCID driver gets matched to the ACR122U and most other
PC/SC readers, with no vendor download needed). Then it lists every PC/SC
reader it finds (any ACR122U-compatible reader works, not just that exact
model) so you can pick the one you plugged in, then asks you to tap the
device you want to unlock with. Tap your phone
(with the companion app open) or your tag — once detected, confirm "yes,
this is the one" and it's registered. An account password is **optional**:
leave it blank if you're setting up Linux Tier 1 (PAM-only), since nothing
will ever type it.

(There's also a CLI version, `python src/main.py enroll`, that asks the same
questions in the terminal if you'd rather not use a browser.)

### 3a. Linux — Tier 1, no typing (recommended)

```bash
sudo bash scripts/setup_pam_linux.sh <pam-service>
```

e.g. `sudo bash scripts/setup_pam_linux.sh light-locker`. Lock your session
and tap your phone — it unlocks with no password prompt at all. Your normal
password still works if the phone isn't there.

### 3b. Linux — Tier 2, or Windows

**Linux:**
```bash
bash scripts/install_service_linux.sh
```
Registers `nfc-unlock-pc.service` as a `systemd --user` unit that starts at
login and types your stored password on tap.

**Windows** (elevated PowerShell):
```powershell
cd scripts
powershell -ExecutionPolicy Bypass -File .\install_task.ps1
```
Registers `NFCUnlockPC`, a Scheduled Task running as SYSTEM at boot that
survives the lock screen.

### Try it

Lock your session (`Win+L` / `Super+L` / `loginctl lock-session`), then tap
your phone on the ACR122U. The reader LED flashes; within ~1.5 seconds (Tier
2) or immediately (Tier 1) your session unlocks.

---

## Project layout

```
nfc-unlock-pc/
├── install.py                    cross-platform installer (detects OS)
├── src/
│   ├── main.py                    entry point (enroll / run / list)
│   └── nfc_unlock/
│       ├── reader.py              ACR122U / PC-SC: physical UID + HCE token (get_identifier)
│       ├── config.py              config.json + OS-keyring password storage
│       ├── enroll.py               enrollment wizard (phone or tag, password optional)
│       ├── unlocker.py              picks the right Tier-2 backend for your OS
│       ├── unlocker_windows.py      SendInput → Winlogon desktop (Windows)
│       ├── unlocker_linux.py        xdotool/wtype (Linux Tier 2)
│       └── service.py               Tier-2 watch loop (typing backends)
├── android-hce-app/               Android companion app (HCE token emulator)
│   └── app/src/main/java/com/nfcunlock/companion/
│       ├── HceService.kt           answers SELECT AID with this device's token
│       ├── TokenStore.kt           generates/stores the token
│       └── MainActivity.kt         shows the token, lets you regenerate it
├── scripts/
│   ├── install_task.ps1            Windows: register SYSTEM scheduled task (Tier 2)
│   ├── uninstall_task.ps1           Windows: remove it
│   ├── install_driver_windows.ps1   Windows: re-scan for hardware changes to fetch a reader driver
│   ├── install_service_linux.sh     Linux: register systemd --user service (Tier 2)
│   ├── pam_nfc_check.py             Linux Tier 1: PAM helper (exit 0/1 based on tap)
│   └── setup_pam_linux.sh           Linux Tier 1: wires pam_nfc_check.py into /etc/pam.d/<service>
├── docs/
│   └── index.html                 project explainer page (GitHub Pages)
├── config.example.json
├── requirements.txt
└── README.md
```

---

## Security notes

- This is a **convenience** project, not a certified authentication system.
  Anyone who can present an enrolled phone/tag to the reader can unlock your
  session — same threat model as a physical office access card.
- Physical MIFARE Classic tags can be cloned relatively easily; NTAG21x are
  better. The HCE token is a 16-byte random value that never leaves the phone
  except over the encrypted NFC field during a tap, and isn't tied to any
  cloneable hardware UID — it's the strongest identifier this project
  supports.
- **Linux Tier 1 (PAM)**: `pam_exec.so ... sufficient` is inserted as the
  *first* line of the chosen service's auth stack. If `pam_nfc_check.py`
  exits non-zero (no reader, no tap within 5s, wrong token), PAM falls
  through to your existing `pam_unix.so` password check unchanged — you are
  never locked out by this, even if the reader is unplugged.
- **Tier 2 (typed password)**: stored via your OS's secure credential store,
  but still retrievable by anything running as you (Linux) or as SYSTEM
  (Windows) — same threat model as saved browser/Windows credentials.

---

## Roadmap

- **Windows passwordless unlock** (a Tier-1 equivalent): would require a
  custom **Credential Provider** (`ICredentialProvider`/`ICredentialProviderCredential`
  COM interfaces) that authenticates via the NFC reader instead of a
  password. This is the Windows-native mechanism — it's how Windows Hello and
  smart-card logon plug in. Deep research for this project turned up no
  actively-maintained open-source reference implementation for an NFC
  Credential Provider; commercial tools like
  [Rohos Logon Key](https://rohos.com/) implement something like this. A
  from-scratch Credential Provider (typically a C++/C# COM DLL registered via
  the registry, implementing `ICredentialProviderFilter` to suppress the
  password tile when the tag is present) is the right design but a
  substantial separate project — tracked here as future work rather than
  promised functionality.
- Multiple enrolled phones/tags (currently one identifier in `config.json`).
- A "lock on phone removal" companion mode (tap to unlock, walk away to
  auto-lock).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No PC/SC readers found` | **Windows**: run `python src/main.py setup` - its first step detects a driverless reader and offers to let Windows fetch a driver for it (`scripts/install_driver_windows.ps1`, runs `pnputil /scan-devices` elevated). If that doesn't help, check Device Manager and restart the "Smart Card" service, or install the ACS driver manually: https://www.acs.com.hk/en/driver/3/acr122u-usb-nfc-reader/. **Linux**: `sudo systemctl status pcscd`, run `pcsc_scan` to confirm the reader is seen. |
| Reader detected but nothing matches | For tags: make sure it's ISO14443-A/MIFARE/NTAG, hold flat for ~1s. For phones: open the companion app first (HCE services often need to have been launched at least once), hold flat against the reader's antenna (usually centered under the ACR122U logo). |
| `pip install -r requirements.txt` fails building `pyscard` on Windows (`Microsoft Visual C++ 14.0 or greater is required`) | Your default Python is too new for prebuilt `pyscard` wheels (cp314+). `python install.py` auto-detects this and creates a `.venv` with an older Python (3.9–3.13) via the `py` launcher — install one from python.org if none is found. |
| Linux Tier 1: tapping doesn't bypass the password prompt | Confirm `<pam-service>` matches what your locker actually uses (`ls /etc/pam.d/`), check the inserted line in `/etc/pam.d/<service>` is the *first* `auth` line, and test `pam_nfc_check.py` manually: `python scripts/pam_nfc_check.py; echo $?` while tapping. |
| Linux Tier 2 / Windows: unlock doesn't type anything | **Windows**: the service must run as SYSTEM (via the scheduled task) — `OpenDesktop("Winlogon")` fails for normal user processes. **Linux**: make sure `xdotool`/`wtype` is installed and the `systemd --user` service has `DISPLAY`/`WAYLAND_DISPLAY`/`XAUTHORITY` set (see `install_service_linux.sh`). |
| Wrong field gets focused (Windows Tier 2) | Adjust the Tab-key logic in `unlocker_windows.py` for your specific lock screen layout (PIN vs password, multiple accounts, etc.) |

---

## Credits / prior art

- [SiRFIDaL](https://github.com/jpetazzo/sirfidal) (Raphael Giraut,
  GPL-3.0) and `pam_nfc` (nfc-tools project) — the `pam_exec.so`
  "external helper decides auth success" pattern used for Linux Tier 1.
- [PAM RFID](https://www.pm-codeworks.de/pamrfid.html) — another
  RFID/PAM integration explored during research.
- [Rohos Logon Key](https://rohos.com/) — the most complete existing
  Windows + ACR122U solution, including a real Credential Provider; referenced
  as the bar for the Windows roadmap item above.

---

## License

MIT — see [LICENSE](LICENSE).
