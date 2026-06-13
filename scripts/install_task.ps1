<#
.SYNOPSIS
    Installs the NFC Unlock service as a SYSTEM Scheduled Task that starts at boot.

.DESCRIPTION
    Must be run from an elevated (Administrator) PowerShell prompt.
    Creates a task named "NFCUnlockPC" that runs as SYSTEM, "whether the user
    is logged on or not", so it survives the lock screen and is able to
    attach to the secure Winlogon desktop to type your credentials.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install_task.ps1
#>

$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Prefer the project virtualenv (created by install.py if the system Python
# had no prebuilt pyscard wheel), otherwise fall back to python/py on PATH.
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $Python) {
        $Python = (Get-Command py -ErrorAction SilentlyContinue).Source
    }
}
if (-not $Python) {
    throw "Python was not found. Run 'python install.py' from the project root first."
}

Write-Host "Using Python: $Python"

$MainScript = Join-Path $ProjectRoot "src\main.py"

$Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$MainScript`" run" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName "NFCUnlockPC" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Watches the ACR122U NFC reader and unlocks Windows when the enrolled phone tag is presented." -Force

Write-Host "Scheduled task 'NFCUnlockPC' installed. It will start automatically on next boot."
Write-Host "To start it immediately: Start-ScheduledTask -TaskName 'NFCUnlockPC'"
