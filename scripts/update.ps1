param([string]$VmName = 'seminar-agentic-ai')
. (Join-Path $PSScriptRoot 'common.ps1')
Assert-LabName $VmName
Get-Command multipass -ErrorAction Stop | Out-Null
Get-Command tar -ErrorAction Stop | Out-Null
Invoke-LabNative 'multipass' @('exec', $VmName, '--', 'sudo', 'cloud-init', 'status', '--wait')
Sync-LabSource $VmName (Split-Path $PSScriptRoot -Parent)
Invoke-LabNative 'multipass' @('exec', $VmName, '--', 'sudo', 'bash', '/opt/seminar-lab/vm/provision-v4.sh')
