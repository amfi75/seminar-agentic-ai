# Shared host primitives, including Windows PowerShell 5.1-compatible process quoting.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function ConvertTo-LabProcessArgument {
    param([AllowEmptyString()][string]$Value)
    # Microsoft CRT quoting: double backslashes before quotes and at a quoted end.
    '"' + ([regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1')) + '"'
}
function Invoke-LabProcess {
    param([string]$Program, [string[]]$Arguments, [int]$TimeoutSeconds = 30)
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $Program
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.Arguments = (($Arguments | ForEach-Object { ConvertTo-LabProcessArgument $_ }) -join ' ')
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $start
    if (-not $process.Start()) { throw "Could not start $Program" }
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        $process.Kill()
        throw "$Program timed out. No automatic reset/recovery was performed."
    }
    $outputText = $stdout.Result
    $errorText = $stderr.Result
    if ($process.ExitCode -ne 0) { throw "$Program failed ($($process.ExitCode)): $errorText $outputText" }
    $outputText
}
function Get-LabWindowsIdentity {
    [Security.Principal.WindowsIdentity]::GetCurrent().Name
}
function Set-LabPrivateFile {
    param([string]$Path, [bool]$Windows = ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT))
    if ($Windows) {
        $identity = Get-LabWindowsIdentity
        # Reset removes stale explicit grants, then remove inherited grants and add this user only.
        & icacls $Path /reset | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not reset managed file ACL.' }
        & icacls $Path /inheritance:r /grant:r "${identity}:(F)" /setowner $identity | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not restrict managed file ACL to its owner.' }
    } else {
        & chmod 600 $Path
        if ($LASTEXITCODE -ne 0) { throw 'Could not restrict managed file permissions.' }
    }
}
function Assert-LabNoLink {
    param([string]$Path)
    $current = $Path
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -Force -LiteralPath $current
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Refusing linked path: $current" }
        }
        $parent = Split-Path $current -Parent
        if ($parent -eq $current) { break }
        $current = $parent
    }
}
function Write-LabUtf8 {
    param([string]$Path, [string]$Text, [Text.Encoding]$Encoding = $null)
    if (-not $Encoding) { $Encoding = New-Object Text.UTF8Encoding $false }
    [IO.File]::WriteAllText($Path, $Text, $Encoding)
}
function Get-LabSshConfiguration {
    param([string]$Original, [string]$Alias, [string]$Address, [string]$Key, [string]$Trust, [bool]$AddressOnly = $false)
    $newline = "`n"
    if ($Original.Contains("`r`n")) { $newline = "`r`n" }
    $lines = @($Original -split '\r?\n')
    if ($lines.Count -gt 0 -and $lines[-1] -eq '') { $lines = @($lines | Select-Object -SkipLast 1) }
    if ($AddressOnly) {
        $managed = $false
        $updated = foreach ($line in $lines) {
            if ($line -eq "# BEGIN managed $Alias") { $managed = $true }
            if ($managed -and $line -match '^\s*HostName\s+') { "  HostName $Address" } else { $line }
            if ($line -eq "# END managed $Alias") { $managed = $false }
        }
        return ($updated -join $newline) + $newline
    }
    $before = New-Object 'Collections.Generic.List[string]'
    $extra = New-Object 'Collections.Generic.List[string]'
    $after = New-Object 'Collections.Generic.List[string]'
    $inside = $false; $found = $false; $finished = $false
    foreach ($line in $lines) {
        if ($line -eq "# BEGIN managed $Alias" -or $line -eq "# END managed $Alias") { continue }
        if ($line -match '^\s*(Host|Match)\s+') {
            if ($inside) { $inside = $false; $finished = $true }
            $words = @($line.Trim() -split '\s+')
            if ($words[0] -ieq 'Host' -and $words[1..($words.Count-1)] -icontains $Alias) {
                if ($found -or $words.Count -ne 2) { throw 'Ambiguous/duplicate Host alias; original preserved.' }
                $found = $true; $inside = $true; continue
            }
        }
        if ($inside) {
            if ($line -notmatch '^\s*(HostName|User|IdentityFile|IdentitiesOnly|HostKeyAlias|UserKnownHostsFile|StrictHostKeyChecking)\s+') { $extra.Add($line) }
        } elseif ($finished) { $after.Add($line) } else { $before.Add($line) }
    }
    $block = @("# BEGIN managed $Alias", "Host $Alias", "  HostName $Address", '  User student',
        "  IdentityFile `"$Key`"", '  IdentitiesOnly yes', "  HostKeyAlias $Alias",
        "  UserKnownHostsFile `"$Trust`"", '  StrictHostKeyChecking yes') + @($extra) + @("# END managed $Alias")
    ((@($before) + $block + @($after)) -join $newline) + $newline
}
