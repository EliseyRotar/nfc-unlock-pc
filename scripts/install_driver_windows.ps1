<#
.SYNOPSIS
    Best-effort, generic driver install/repair for a connected NFC/smart-card
    reader (ACR122U or any other PC/SC-class reader).

.DESCRIPTION
    Most ACR122U-compatible readers work today with Windows' INBOX USB CCID
    smart-card class driver (usbccid.sys) - no vendor driver download needed.
    When Windows hasn't matched the device to that driver yet (e.g. it shows
    up as an "Unknown device" or with a yellow-bang in Device Manager), the
    fix is almost always to make Windows re-scan for hardware changes with
    permission to fetch a driver from Windows Update / its local driver
    store - exactly what Device Manager's "Scan for hardware changes" /
    "Update driver -> Search automatically" does.

    This script does that generically via `pnputil /scan-devices`, which
    works for the ACR122U and for most other PC/SC USB readers alike - no
    hardcoded vendor download URLs (which go stale and would be a supply-
    chain risk to auto-download and silently execute).

    Must be run elevated (the setup wizard launches it via
    `Start-Process -Verb RunAs`, which prompts for admin consent).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install_driver_windows.ps1
#>

Write-Host "Re-scanning for hardware changes (this lets Windows fetch a matching"
Write-Host "driver from Windows Update / its local driver store for any new or"
Write-Host "unrecognized NFC/smart-card reader)..."

pnputil /scan-devices

Write-Host ""
Write-Host "Done. Give it a few seconds, then click 'Refresh' in the setup wizard."
Write-Host ""
Write-Host "If your reader still isn't detected after this, it likely needs a"
Write-Host "vendor driver - for the ACS ACR122U, get it from:"
Write-Host "  https://www.acs.com.hk/en/driver/3/acr122u-usb-nfc-reader/"

Start-Sleep -Seconds 2
