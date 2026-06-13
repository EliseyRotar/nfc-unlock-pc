<#
.SYNOPSIS
    Removes the NFC Unlock scheduled task.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\uninstall_task.ps1
#>

Unregister-ScheduledTask -TaskName "NFCUnlockPC" -Confirm:$false
Write-Host "Scheduled task 'NFCUnlockPC' removed."
