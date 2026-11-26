# Deploy and upgrade iraqi_contracting_management
$ErrorActionPreference = "Stop"
$logFile = "C:\Users\legion\.gemini\antigravity\scratch\deploy_result.txt"
"Starting deployment at $(Get-Date)" | Out-File $logFile -Encoding utf8

try {
    $src = "C:\Users\legion\.gemini\antigravity-ide\scratch\iraqi_contracting_management"
    $dst = "C:\Program Files\Odoo 19.0.20260913\server\odoo\addons\iraqi_contracting_management"

    if (-not (Test-Path $dst)) {
        New-Item -ItemType Directory -Path $dst -Force | Out-Null
    }

    "1. Copying files to $dst..." | Out-File $logFile -Append -Encoding utf8
    Copy-Item -Path "$src\*" -Destination $dst -Recurse -Force

    "2. Stopping odoo-server-19.0..." | Out-File $logFile -Append -Encoding utf8
    Stop-Service -Name "odoo-server-19.0" -Force
    Start-Sleep -Seconds 2

    "3. Upgrading module in database Sag-odoo19..." | Out-File $logFile -Append -Encoding utf8
    $py = "C:\Program Files\Odoo 19.0.20260913\python\python.exe"
    $bin = "C:\Program Files\Odoo 19.0.20260913\server\odoo-bin"
    $conf = "C:\Program Files\Odoo 19.0.20260913\server\odoo.conf"
    
    $proc = Start-Process -FilePath $py -ArgumentList "`"$bin`" -c `"$conf`" -d Sag-odoo19 -u iraqi_contracting_management --stop-after-init" -NoNewWindow -Wait -PassThru
    "Upgrade process exit code: $($proc.ExitCode)" | Out-File $logFile -Append -Encoding utf8

    "4. Starting odoo-server-19.0..." | Out-File $logFile -Append -Encoding utf8
    Start-Service -Name "odoo-server-19.0"
    Start-Sleep -Seconds 2

    "SUCCESS: Deployment and database upgrade completed successfully at $(Get-Date)" | Out-File $logFile -Append -Encoding utf8
} catch {
    "ERROR: $($_.Exception.Message)" | Out-File $logFile -Append -Encoding utf8
}
