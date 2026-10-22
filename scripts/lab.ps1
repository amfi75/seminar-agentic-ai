param([string]$Action = 'help', [string]$VmName = 'seminar-agentic-ai')
. (Join-Path $PSScriptRoot 'lab-common.ps1')
$projectRoot = Split-Path $PSScriptRoot -Parent
$labHome = if ($env:SEMINAR_LAB_HOME) { $env:SEMINAR_LAB_HOME } else { $HOME }
if ($Action -notin @('setup','open','pause','stop','status')) {
    Write-Host 'Usage: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\lab.ps1 setup|open|pause|stop|status [seminar-agentic-ai[-NAME]]'
    Write-Host 'Install Multipass, OpenSSH Client, and VS Code first. Complete administrator/passphrase/Trust dialogs locally.'
    if ($Action -in @('help','--help','-h')) { exit 0 }; exit 1
}
try {
    if ($VmName -notmatch '^seminar-agentic-ai(-[a-z0-9-]+)?$') { throw 'Use a seminar-agentic-ai VM name.' }
    $aliasName = 'seminar-lab'
    if ($VmName -ne 'seminar-agentic-ai') { $aliasName += '-' + $VmName.Substring('seminar-agentic-ai-'.Length) }
    $mpCommand = Get-Command multipass -ErrorAction SilentlyContinue
    if (-not $mpCommand) { throw 'Install Multipass from https://canonical.com/multipass/install, complete its virtualization prerequisites, and reopen PowerShell.' }
    $mp = $mpCommand.Source
    function Invoke-LabMultipass { param([string[]]$A, [int]$Limit=30) Invoke-LabProcess $mp $A $Limit }
    $inventory = (Invoke-LabMultipass @('list','--format','json')) | ConvertFrom-Json
    $matches = @($inventory.list | Where-Object { $_.name -eq $VmName })
    $state = if ($matches.Count) { $matches[0].state } else { 'Absent' }
    if ($Action -eq 'status') {
        Write-Host "VM: $VmName State: $state"
        if ($state -eq 'Running') {
            try { Write-Host (Invoke-LabMultipass @('exec',$VmName,'--','sudo','python3','/opt/seminar-lab/management/install_workflow.py','--probe')) } catch { Write-Host 'Convenience layer unavailable; run setup.' }
            Write-Host 'Separate application check (an intentional scenario can fail this):'
            Write-Host (Invoke-LabMultipass @('exec',$VmName,'--','sudo','/usr/local/sbin/lab-admin','verify'))
        }
        exit 0
    }
    if ($Action -in @('pause','stop')) {
        Write-Host 'Save editor work first. VS Code will disconnect; no VM/profile is deleted.'
        if (($Action -eq 'pause' -and $state -eq 'Suspended') -or ($Action -eq 'stop' -and $state -eq 'Stopped')) { Write-Host "Already $state"; exit 0 }
        if ($state -ne 'Running' -and -not ($Action -eq 'stop' -and $state -eq 'Suspended')) { throw "Cannot $Action a VM in $state state." }
        $operation = if ($Action -eq 'pause') { 'suspend' } else { 'stop' }
        Write-Host (Invoke-LabMultipass @($operation,$VmName) 120); exit 0
    }
    $windowsHost = [Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT
    if ($windowsHost -and $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'Windows ARM/other architectures are outside the documented target.' }
    foreach ($tool in @('ssh','ssh-keygen','tar')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Missing $tool. Install OpenSSH Client through Windows Optional Features; use the tar supplied by supported Windows versions. See docs/start-here.md." }
    }
    $codeCommand = Get-Command code -ErrorAction SilentlyContinue
    $codePath = if ($codeCommand) { $codeCommand.Source } else { $null }
    if (-not $codePath) {
        $candidates = @()
        if ($env:LOCALAPPDATA) { $candidates += Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code\bin\code.cmd' }
        if ($env:ProgramFiles) { $candidates += Join-Path $env:ProgramFiles 'Microsoft VS Code\bin\code.cmd' }
        $candidates += '/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code'
        $codePath = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    }
    if (-not $codePath) { throw 'Install VS Code: https://code.visualstudio.com/download' }
    function Code { param([string[]]$A) $result = & $codePath @A; if ($LASTEXITCODE -ne 0) { throw 'VS Code CLI failed; retain its output.' }; $result }
    $settings = if ($windowsHost) { Join-Path $env:APPDATA 'Code\User\settings.json' } else { Join-Path $labHome 'Library/Application Support/Code/User/settings.json' }
    if ((Test-Path -LiteralPath $settings) -and ([IO.File]::ReadAllText($settings) -match '"remote.SSH.configFile"\s*:\s*"[^"]+"')) { throw 'VS Code overrides remote.SSH.configFile. Select your standard ~/.ssh/config in Settings; unrelated preferences were preserved.' }
    if ($Action -eq 'setup') {
        Write-Host 'Reference guest: 4 vCPU / 8 GiB RAM / 40 GiB disk; allow additional space for host applications.'
        Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free | Out-Host
        if ($windowsHost) { Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory | Out-Host }
    }
    if ($state -eq 'Absent') {
        if ($Action -ne 'setup') { throw 'Run setup first; open does not create a VM.' }
        & (Join-Path $PSScriptRoot 'create.ps1') -VmName $VmName
        if ($LASTEXITCODE -ne 0) { throw 'Creation/provisioning failed; preserve the partial VM.' }
    } elseif ($state -in @('Stopped','Suspended')) {
        Write-Host (Invoke-LabMultipass @('start',$VmName,'--timeout','300') 330)
    } elseif ($state -ne 'Running') { throw "VM is $state. Preserve it and diagnose." }
    $installer = '/opt/seminar-lab/management/install_workflow.py'
    $guestStage = $null
    if ($Action -eq 'setup') {
        $guestStage = (Invoke-LabMultipass @('exec',$VmName,'--','mktemp','-d','/home/ubuntu/lab-workflow.XXXXXX')).Trim()
        if ($guestStage -notmatch '^/home/ubuntu/lab-workflow\.[A-Za-z0-9]+$') { throw 'Unexpected staging path.' }
        foreach ($file in @('install_workflow.py','workflow.py','fresh_trial_entry.py','workflow-start.md')) {
            Write-Host (Invoke-LabMultipass @('transfer',(Join-Path $projectRoot "management/$file"),"${VmName}:$guestStage/$file"))
        }
        $installer = "$guestStage/install_workflow.py"
    }
    $probe = $null
    $readyAttempts = 30
    if ($env:SEMINAR_LAB_READY_ATTEMPTS) { $readyAttempts = [int]$env:SEMINAR_LAB_READY_ATTEMPTS }
    if ($readyAttempts -lt 1 -or $readyAttempts -gt 30) { throw 'Readiness attempts must be 1..30.' }
    for ($attempt=0; $attempt -lt $readyAttempts; $attempt++) {
        try { $probe = (Invoke-LabMultipass @('exec',$VmName,'--','sudo','python3',$installer,'--probe')) | ConvertFrom-Json; if ($probe.ready) { break } } catch { $probe = $null }
        Start-Sleep -Seconds 2
    }
    if (-not $probe -or -not $probe.ready) { throw 'Not a ready recognized v5 lab. Run setup if the layer is absent; diagnose services otherwise. No reset performed.' }
    if ($Action -eq 'setup' -and $probe.active_opencode) { throw 'Stop OpenCode before installing convenience files. Profile unchanged.' }
    $sshDirectory = Join-Path $labHome '.ssh'
    $key = Join-Path $sshDirectory $aliasName
    $trust = Join-Path $sshDirectory "known_hosts.$aliasName"
    $config = Join-Path $sshDirectory 'config'
    foreach ($path in @($sshDirectory,$key,"$key.pub",$trust,$config)) { Assert-LabNoLink $path }
    if (-not (Test-Path -LiteralPath $sshDirectory)) { New-Item -ItemType Directory -Path $sshDirectory | Out-Null }
    if (-not (Test-Path -LiteralPath $key)) {
        if ($Action -ne 'setup') { throw 'Dedicated key absent; run setup.' }
        Write-Host 'Create the lab key. A passphrase is recommended; choosing empty is your explicit local choice.'
        & ssh-keygen -t ed25519 -f $key
        if ($LASTEXITCODE -ne 0) { throw 'Key creation failed.' }
    }
    Set-LabPrivateFile $key
    if (-not (Test-Path -LiteralPath "$key.pub")) {
        $publicKey = & ssh-keygen -y -f $key
        if ($LASTEXITCODE -ne 0) { throw 'Cannot derive public key.' }
        Write-LabUtf8 "$key.pub" (($publicKey -join "`n") + "`n")
    }
    # ssh-keygen prefers an adjacent .pub. Inspect a restricted temporary copy without one.
    $keyCheck = Join-Path $sshDirectory ('.key-check-' + [guid]::NewGuid().ToString('N'))
    try {
        New-Item -ItemType File -Path $keyCheck -ErrorAction Stop | Out-Null
        Set-LabPrivateFile $keyCheck
        [IO.File]::WriteAllBytes($keyCheck, [IO.File]::ReadAllBytes($key))
        $privateFingerprint = & ssh-keygen -lf $keyCheck
        if ($LASTEXITCODE -ne 0) { throw 'Could not inspect dedicated identity.' }
    } finally { Remove-Item -LiteralPath $keyCheck -ErrorAction SilentlyContinue }
    $publicFingerprint = & ssh-keygen -lf "$key.pub"
    if ($LASTEXITCODE -ne 0 -or (($privateFingerprint -split '\s+')[1] -ne ($publicFingerprint -split '\s+')[1])) { throw 'Public and private identity do not match; existing keys preserved.' }
    $publicKey = [IO.File]::ReadAllText("$key.pub").Trim()
    if ($publicKey -notmatch '^ssh-ed25519 ') { throw 'Expected an Ed25519 key; existing identities were not overwritten.' }
    $info = (Invoke-LabMultipass @('info',$VmName,'--format','json')) | ConvertFrom-Json
    $address = $info.info.PSObject.Properties[$VmName].Value.ipv4[0]
    if ($address -notmatch '^\d+\.\d+\.\d+\.\d+$' -or $address -match '^(10\.79\.|172\.17\.)') { throw 'No usable host-reachable VM address.' }
    $keyParts = ((Invoke-LabMultipass @('exec',$VmName,'--','sudo','cat','/etc/ssh/ssh_host_ed25519_key.pub')).Trim() -split '\s+')
    if ($keyParts[0] -ne 'ssh-ed25519') { throw 'Could not obtain trusted VM public identity.' }
    $trusted = "$aliasName $($keyParts[0]) $($keyParts[1])"
    if ((Test-Path -LiteralPath $trust) -and [IO.File]::ReadAllText($trust).Trim() -ne $trusted) {
        if ($Action -ne 'setup') { throw 'VM host identity changed. If intentionally rebuilt, use setup to re-enroll through Multipass.' }
        if ((Read-Host "Confirm intentional rebuild by typing $VmName") -ne $VmName) { throw 'Trust unchanged.' }
        Copy-Item -LiteralPath $trust -Destination "$trust.before-workflow-$([DateTime]::UtcNow.Ticks)"
    }
    if (-not (Test-Path -LiteralPath $trust) -or [IO.File]::ReadAllText($trust).Trim() -ne $trusted) {
        if ($Action -ne 'setup') { throw 'Managed trust absent; run setup.' }
        Write-LabUtf8 $trust ($trusted + "`n"); Set-LabPrivateFile $trust
    }
    $configEncoding = New-Object Text.UTF8Encoding $false
    if (Test-Path -LiteralPath $config) {
        $bytes = [IO.File]::ReadAllBytes($config)
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) { $configEncoding = New-Object Text.UTF8Encoding $true }
        elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 255 -and $bytes[1] -eq 254) { $configEncoding = [Text.Encoding]::Unicode }
        elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 254 -and $bytes[1] -eq 255) { $configEncoding = [Text.Encoding]::BigEndianUnicode }
    }
    $original = if (Test-Path -LiteralPath $config) { [IO.File]::ReadAllText($config) } else { '' }
    if (-not $original.Contains("# BEGIN managed $aliasName")) {
        if ($Action -ne 'setup') { throw 'Run setup to adopt the standard connection.' }
        if ($original -match "(?im)^\s*Host\s+.*$([regex]::Escape($aliasName))") {
            $effective = (Invoke-LabProcess 'ssh' @('-G',$aliasName)) -split '\r?\n'
            if ($effective -notcontains "hostname $address" -or $effective -notcontains 'user student') { throw 'Existing alias targets another identity; preserve and resolve it.' }
            $originalIdentities = @($effective | Where-Object { $_ -match '^identityfile ' })
            if ($originalIdentities.Count -ne 1 -or ($originalIdentities[0] -ne "identityfile ~/.ssh/$aliasName" -and $originalIdentities[0] -ne "identityfile $key")) { throw 'Existing alias uses additional/different identities; preserved.' }
        }
    }
    $new = Get-LabSshConfiguration $original $aliasName $address $key $trust ($Action -eq 'open')
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ('lab-ssh-' + [guid]::NewGuid().ToString('N'))
    try {
        Write-LabUtf8 $temporary $new $configEncoding
        $effective = (Invoke-LabProcess 'ssh' @('-G','-F',$temporary,$aliasName)) -split '\r?\n'
        foreach ($expected in @("hostname $address",'user student','identitiesonly yes','stricthostkeychecking true',"hostkeyalias $aliasName","userknownhostsfile $trust")) {
            if ($effective -notcontains $expected) { throw 'An SSH rule overrides the managed connection; original configuration preserved.' }
        }
        $identities = @($effective | Where-Object { $_ -match '^identityfile ' })
        if ($identities.Count -ne 1 -or $identities[0] -ne "identityfile $key") { throw 'An SSH wildcard/include adds a divergent identity. Original configuration preserved.' }
    } finally { Remove-Item -LiteralPath $temporary -ErrorAction SilentlyContinue }
    if ($original -ne $new) {
        if (Test-Path -LiteralPath $config) { Copy-Item -LiteralPath $config -Destination "$config.before-workflow-$([DateTime]::UtcNow.Ticks)" }
        Write-LabUtf8 $config $new $configEncoding; Set-LabPrivateFile $config
    }
    if ($Action -eq 'setup') {
        Write-Host (Invoke-LabMultipass @('exec',$VmName,'--','sudo','python3',$installer,'--authorize-key',$publicKey))
        Write-Host (Invoke-LabMultipass @('exec',$VmName,'--','sudo','python3',$installer,'--source-dir',$guestStage))
        Write-Host (Invoke-LabMultipass @('exec',$VmName,'--','rm','-r',$guestStage))
        Code @('--install-extension','ms-vscode-remote.remote-ssh') | Out-Host
    }
    & ssh -o ConnectTimeout=10 $aliasName true
    if ($LASTEXITCODE -ne 0) { throw 'SSH failed; check passphrase/key/trust. No identity checks disabled.' }
    Write-Host 'Connection ready. Separate application check (an outage is preserved):'
    try { Write-Host (Invoke-LabMultipass @('exec',$VmName,'--','sudo','/usr/local/sbin/lab-admin','verify')) } catch { Write-Host 'Application check failed; existing scenario preserved. No reset.' }
    Code @('--remote',"ssh-remote+$aliasName",'--install-extension','srl-labs.vscode-containerlab@0.26.3') | Out-Host
    $extensions = @(Code @('--remote',"ssh-remote+$aliasName",'--list-extensions','--show-versions'))
    if ($extensions -notcontains 'srl-labs.vscode-containerlab@0.26.3') { throw 'Could not verify remote Containerlab installation. No manual fallback assumed.' }
    Code @('--new-window','--remote',"ssh-remote+$aliasName",'/home/student/labs/control/lab.code-workspace') | Out-Host
    Write-Host 'VS Code launch requested. Complete native Trust/Linux/passphrase dialogs, then use Tasks: Run Task → Lab: ...'
} catch {
    Write-Error "Lab: $_"
    exit 1
}
