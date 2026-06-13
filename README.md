# NFC Unlock PC

Tap your phone on a USB **ACR122U NFC reader** to unlock your **PC** — works
on both **Windows** and **Linux**. No extra app on the phone required, just
an NFC tag (sticker) attached to it.

The reader's LED turns green and beeps when it sees a tag; this project
watches for that event, checks the tag's UID against the one you enrolled,
and types your account password for you to unlock the session.

---

## How it works

```
 ┌──────────────┐      tap       ┌────────────┐   PC/SC (pyscard)   ┌──────────────────┐
 │ Phone w/ NFC  │ ──────────────▶│  ACR122U   │ ───────────────────▶│ nfc-unlock-pc     │
 │ tag/sticker   │                │  USB reader│                     │ background service│
 └──────────────┘                └────────────┘                     └─────────┬─────────┘
                                                                                │ matches enrolled UID?
                                                                                ▼
                                                  ┌───────────────────────────────────────────┐
                                                  │ Windows: SendInput → Winlogon secure desktop │
                                                  │ Linux:   xdotool/wtype → your X11/Wayland     │
                                                  │          session lock screen                 │
                                                  └───────────────────────────────────────────┘
```

* The ACR122U shows up as a standard **PC/SC smart-card reader** on both
  Windows and Linux, so we talk to it with the Python
  [`pyscard`](https://pypi.org/project/pyscard/) library — no vendor SDK
  required.
* We read the tag's UID with the `FF CA 00 00 00` "Get UID" APDU, which works
  for MIFARE / NTAG / ISO14443-A tags (the cheap stickers you can buy in
  packs of 10, or write with any "NFC Tools" phone app).
* Your account password is stored in the **OS-native secure credential
  store** via [`keyring`](https://pypi.org/project/keyring/) (Windows
  Credential Manager / Linux Secret Service / KWallet) — never in plain text,
  never in `config.json`.
* **Windows**: the lock screen runs on an isolated "Winlogon" secure desktop
  that normal apps can't send keystrokes to, so the service runs as
  **SYSTEM** via a Scheduled Task (`scripts/install_task.ps1`), which *is*
  allowed to attach to that desktop (`OpenDesktop`/`SetThreadDesktop` +
  `SendInput`).
* **Linux**: screen lockers (i3lock, light-locker, xscreensaver, swaylock,
  hyprlock, ...) run *inside your own user session*, so a normal
  `systemd --user` service (`scripts/install_service_linux.sh`) can type into
  them directly via `xdotool` (X11) or `wtype` (Wayland/wlroots) — no root
  needed.

If you'd rather use a polished, ready-made commercial tool for Windows that
supports the ACR122U + MIFARE tags out of the box with proper
credential-provider integration, see **[Rohos Logon Key](https://rohos.com/)**
— it was the most mature existing solution found during research.

---

## Hardware / prerequisites

1. **ACR122U USB NFC reader** (or compatible clone).
2. **An NFC tag** (NTAG213/215/216 or MIFARE Classic sticker) stuck on your
   phone's case — most phones don't natively *emulate* a passive tag, so a
   cheap sticker is the simplest and most reliable approach.
3. Windows 10/11, or Linux (X11 or a wlroots-based Wayland compositor such as
   Sway/Hyprland for the `wtype` path).
4. [Python 3.10+](https://www.python.org/downloads/) on PATH.

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
- **Windows**: installs the Python requirements and reminds you to install
  the official ACR122U driver.
- **macOS**: installs the Python requirements (PC/SC is built in).

Then on every platform:

```bash
python src/main.py enroll
```

Place your phone on the reader when prompted, then enter the
username/password to type at unlock time. The password goes straight into
your OS keyring.

### Windows: install the background task (elevated PowerShell)

```powershell
cd scripts
powershell -ExecutionPolicy Bypass -File .\install_task.ps1
```

Registers `NFCUnlockPC`, a Scheduled Task running as SYSTEM at boot that
survives the lock screen.

### Linux: install the background service

```bash
bash scripts/install_service_linux.sh
```

Registers `nfc-unlock-pc.service` as a `systemd --user` unit that starts at
login.

### Try it

Lock your session (`Win+L` / `Super+L` / `loginctl lock-session`), then tap
your phone on the ACR122U. The reader LED should flash, and within ~1.5
seconds your password should be typed and the session unlocked.

---

## Project layout

```
nfc-unlock-pc/
├── install.py                cross-platform installer (detects OS)
├── src/
│   ├── main.py                entry point (enroll / run / list)
│   └── nfc_unlock/
│       ├── reader.py          ACR122U / PC-SC polling via pyscard (cross-platform)
│       ├── config.py          config.json + OS-keyring password storage
│       ├── enroll.py           enrollment wizard
│       ├── unlocker.py          picks the right backend for your OS
│       ├── unlocker_windows.py  SendInput → Winlogon desktop (Windows)
│       ├── unlocker_linux.py    xdotool/wtype (Linux)
│       └── service.py           main watch loop
├── scripts/
│   ├── install_task.ps1         Windows: register SYSTEM scheduled task
│   ├── uninstall_task.ps1        Windows: remove it
│   └── install_service_linux.sh  Linux: register systemd --user service
├── docs/
│   └── index.html             project explainer page (GitHub Pages)
├── config.example.json
├── requirements.txt
└── README.md
```

---

## Security notes

- Anyone who can place an enrolled (or cloned) tag on the reader can unlock
  your session. MIFARE Classic tags can be cloned relatively easily; NTAG21x
  are better but still just a UID check here — this is a **convenience**
  project, not a high-security authentication system.
- The password is stored via your OS's secure credential store, but is still
  retrievable by anything running as you (Linux) or as SYSTEM (Windows) —
  same threat model as saved browser/Windows credentials in general.
- Treat this like a smart "remember my password and type it for me when I
  tap my phone" tool, not like Windows Hello / FIDO2 / PAM-based 2FA.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No PC/SC readers found` | **Windows**: install the ACS driver, check Device Manager, restart the Smart Card service. **Linux**: `sudo systemctl status pcscd`, run `pcsc_scan` to confirm the reader is seen. |
| Reader detected but `get_uid` always `None` | Make sure the tag is an ISO14443-A / MIFARE / NTAG tag, hold it flat on the reader for ~1s |
| Windows: unlock doesn't type anything | The service must run as SYSTEM (via the scheduled task) — `OpenDesktop("Winlogon")` fails for normal user processes |
| Linux: unlock doesn't type anything | Make sure `xdotool` (X11) or `wtype` (Wayland) is installed, and that the `systemd --user` service has the correct `DISPLAY`/`WAYLAND_DISPLAY`/`XAUTHORITY` env vars (see `install_service_linux.sh`) |
| Wrong field gets focused (Windows) | Adjust the Tab-key logic in `unlocker_windows.py` for your specific lock screen layout (PIN vs password, multiple accounts, etc.) |

---

## License

MIT — see [LICENSE](LICENSE).
