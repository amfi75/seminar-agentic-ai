# Shared PowerShell helpers; compatible with Windows PowerShell 5.1 and PowerShell 7.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-LabNative {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed with exit code $LASTEXITCODE. Stop here and diagnose the output above."
    }
}

function Assert-LabName {
    param([string]$Name)
    if ($Name -notmatch '^seminar-agentic-ai(-[a-z0-9-]+)?$') { throw 'Use a seminar-agentic-ai name.' }
}

function Sync-LabSource {
    param([string]$VmName, [string]$ProjectRoot)
    $stage = Join-Path ([System.IO.Path]::GetTempPath()) ('seminar-lab-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage | Out-Null
    Push-Location $ProjectRoot
    try {
        $archive = Join-Path $stage 'source.tar.gz'
        $list = Join-Path $ProjectRoot 'STUDENT-FILES.txt'
        if (-not (Test-Path -LiteralPath $list -PathType Leaf)) { throw 'Missing student source file list' }
        foreach ($relative in Get-Content -LiteralPath $list) {
            if ($relative.StartsWith('-') -or $relative -notmatch '^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$' -or
                ($relative.Split('/') | Where-Object { $_ -in @('.', '..', '.git') })) { throw 'Unsafe student source path' }
            $path = Join-Path $ProjectRoot $relative
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing student source: $relative" }
            $cursor = Get-Item -LiteralPath $path -Force
            while ($null -ne $cursor -and $cursor.FullName -ne (Get-Item -LiteralPath $ProjectRoot).FullName) {
                if ($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked student source path refused' }
                if ($cursor -is [IO.FileInfo]) { $cursor = $cursor.Directory } else { $cursor = $cursor.Parent }
            }
        }
        Invoke-LabNative 'tar' @('-czf', $archive, '-T', $list)
        Invoke-LabNative 'multipass' @('transfer', $archive, "${VmName}:/home/ubuntu/v4-source.tar.gz")
        # Transfer the shared guest program instead of transporting a shell string
        # through Windows native argument quoting.
        Invoke-LabNative 'multipass' @('transfer', (Join-Path $ProjectRoot 'vm/unpack-source.sh'), "${VmName}:/home/ubuntu/lab-unpack-source.sh")
        Invoke-LabNative 'multipass' @('exec', $VmName, '--', 'sudo', 'bash', '/home/ubuntu/lab-unpack-source.sh')
    }
    finally {
        Pop-Location
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
