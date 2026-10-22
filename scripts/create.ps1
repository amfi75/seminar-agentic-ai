param([string]$VmName = 'seminar-agentic-ai')
. (Join-Path $PSScriptRoot 'common.ps1')
Assert-LabName $VmName
$projectRoot = Split-Path $PSScriptRoot -Parent
Get-Command multipass -ErrorAction Stop | Out-Null
Get-Command tar -ErrorAction Stop | Out-Null
# Query the complete inventory: service errors must not be mistaken for an absent VM.
$inventoryText = Invoke-LabNative 'multipass' @('list', '--format', 'json')
$inventory = ($inventoryText -join "`n") | ConvertFrom-Json
if (@($inventory.list | Where-Object { $_.name -eq $VmName }).Count -gt 0) {
    throw 'VM already exists. Preserve it; use update.ps1 deliberately or choose a fresh lab name.'
}
Invoke-LabNative 'multipass' @('launch', '24.04', '--name', $VmName, '--cpus', '4', '--memory', '8G', '--disk', '40G', '--cloud-init', (Join-Path $projectRoot 'vm/cloud-init.yaml'), '--timeout', '900')
& (Join-Path $PSScriptRoot 'update.ps1') -VmName $VmName
