<#
.SYNOPSIS
Khởi động môi trường SSI local theo Fresh-chain hoặc Keep-chain.

.DESCRIPTION
Fresh-chain tạo Hardhat node mới trên cổng riêng, deploy một bộ contract mới với
manifest có ID riêng, cấp ISSUER_ROLE, rồi khởi động Kubo và ba dashboard.
Keep-chain chỉ xác minh node/manifest đang có và khởi động các dịch vụ còn thiếu;
không deploy hoặc thay đổi blockchain. Secrets chỉ được đọc bởi ứng dụng từ .env
và không được in ra màn hình hay ghi vào state/log của script.

.EXAMPLE
.\start-local.ps1
.\start-local.ps1 -Mode Fresh
.\start-local.ps1 -Mode Keep -DeploymentId m1clean20261119
.\start-local.ps1 -Stop
#>
[CmdletBinding()]
param(
    [ValidateSet('Fresh', 'Keep')]
    [string]$Mode,
    [ValidatePattern('^[a-zA-Z0-9_]{1,64}$')]
    [string]$DeploymentId,
    [switch]$Stop,
    [int]$RpcPort = 18545,
    [int]$HolderPort = 8501,
    [int]$IssuerPort = 8502,
    [int]$VerifierPort = 8503,
    [string]$KuboPath = 'C:\Users\MR DAI\Apps\kubo_v0.43.1\kubo\ipfs.exe'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSCommandPath
$StateFile = Join-Path $env:TEMP 'is355-r11-ssi-start-local.json'
$LogDirectory = Join-Path $env:TEMP 'is355-r11-ssi-logs'
$script:Run = [ordered]@{ deploymentId = $null; rpcUrl = $null; chainId = $null; genesisHash = $null; manifest = $null }

function Fail([string]$Message) { throw "START-LOCAL: $Message" }
function Info([string]$Message) { Write-Host "[SSI] $Message" -ForegroundColor Cyan }
function Ok([string]$Message) { Write-Host "[SSI] $Message" -ForegroundColor Green }

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "Không tìm thấy $Name trong PATH. Cài đặt dependency rồi chạy lại."
    }
}

function Port-Owner([int]$Port) {
    @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
}

function Assert-Port-Free([int]$Port, [string]$Label) {
    $owners = Port-Owner $Port
    if ($owners.Count -gt 0) {
        Fail "$Label không thể khởi động vì cổng $Port đang do PID $($owners -join ', ') sử dụng. Script không tự dừng tiến trình khác."
    }
}

function Wait-Http([string]$Uri, [string]$Label, [int]$TimeoutSeconds = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Milliseconds 750
    } while ((Get-Date) -lt $deadline)
    Fail "$Label không trả HTTP 200 sau $TimeoutSeconds giây. Kiểm tra cổng, vai trò dashboard và log tại $LogDirectory."
}

function Get-RpcChainId([string]$RpcUrl) {
    $payload = @{ jsonrpc = '2.0'; id = 1; method = 'eth_chainId'; params = @() } | ConvertTo-Json -Compress
    try {
        $value = (Invoke-RestMethod -Method Post -Uri $RpcUrl -ContentType 'application/json' -Body $payload -TimeoutSec 3).result
        if (-not $value) { return $null }
        return [Convert]::ToInt64($value.Substring(2), 16)
    } catch { return $null }
}

function Track-HardhatListener([int]$Port, [hashtable]$Started) {
    $owners = Port-Owner $Port
    if ($owners.Count -eq 1) {
        $listenerId = [int]$owners[0]
        if (-not $Started.ContainsKey('hardhat') -or [int]$Started['hardhat'].pid -ne $listenerId) {
            # npx.cmd can be a short-lived launcher and the Node listener can be a
            # child process. Track the listener separately without discarding the launcher.
            Register-ManagedProcess $Started 'hardhat' $listenerId 'hardhat' $Port
        }
    }
    return $owners
}

function Track-ProcessDescendants([int]$ParentProcessId, [hashtable]$Started) {
    $queue = [System.Collections.Generic.Queue[int]]::new()
    $seen = [System.Collections.Generic.HashSet[int]]::new()
    $queue.Enqueue($ParentProcessId)
    while ($queue.Count -gt 0) {
        $parent = $queue.Dequeue()
        $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$parent" -ErrorAction SilentlyContinue)
        foreach ($child in $children) {
            $childId = [int]$child.ProcessId
            if (-not $seen.Add($childId)) { continue }
            # conhost.exe is Windows console infrastructure, not a process started
            # by Hardhat. Its lifecycle can outlive or change independently of the
            # launcher, so it must never become a managed application process.
            if ([System.IO.Path]::GetFileName([string]$child.ExecutablePath) -ieq 'conhost.exe') { continue }
            $entryName = "hardhat-child-$childId"
            if (-not $Started.ContainsKey($entryName)) {
                # A listener may not be ready yet. Keep a verifiable record of
                # every descendant launched by npx so a timeout is still recoverable.
                Register-ManagedProcess $Started $entryName $childId 'hardhat-child' $null
            }
            $queue.Enqueue($childId)
        }
    }
}

function Wait-Rpc([string]$RpcUrl, [int]$Port, [hashtable]$Started) {
    $deadline = (Get-Date).AddSeconds(45)
    do {
        if ($Started.ContainsKey('hardhat-launcher')) {
            Track-ProcessDescendants ([int]$Started['hardhat-launcher'].pid) $Started
        }
        Track-HardhatListener $Port $Started | Out-Null
        $chainId = Get-RpcChainId $RpcUrl
        if ($chainId -eq 31337) { return $chainId }
        Start-Sleep -Milliseconds 750
    } while ((Get-Date) -lt $deadline)
    Fail "RPC $RpcUrl chưa sẵn sàng hoặc không phải chain ID 31337."
}

function Read-DotEnvValue([string]$Name) {
    $envFile = Join-Path $Root '.env'
    if (-not (Test-Path $envFile)) { Fail 'Thiếu .env. Sao chép .env.example rồi điền ví local/testnet.' }
    $match = Get-Content $envFile | Where-Object { $_ -match "^\s*$([regex]::Escape($Name))\s*=\s*(.+?)\s*$" } | Select-Object -Last 1
    if (-not $match) { return $null }
    return ($match -replace "^\s*$([regex]::Escape($Name))\s*=\s*", '').Trim(' ', '"', "'")
}

function Require-IssuerAddress() {
    $issuer = Read-DotEnvValue 'ISSUER_ADDRESS'
    if (-not $issuer -or $issuer -notmatch '^0x[0-9a-fA-F]{40}$' -or $issuer -eq '0x0000000000000000000000000000000000000000') {
        Fail 'ISSUER_ADDRESS trong .env không hợp lệ. Không hiển thị hay sửa .env tự động.'
    }
    return $issuer
}

function New-DeploymentId() {
    $stamp = Get-Date -Format 'yyyyMMddHHmmss'
    $suffix = [Guid]::NewGuid().ToString('N').Substring(0, 8)
    return "fresh_${stamp}_$suffix"
}

function Manifest-Path([string]$Id) {
    return Join-Path $Root "deployments\localhost.$Id.json"
}

function Read-Manifest([string]$Id) {
    $path = Manifest-Path $Id
    if (-not (Test-Path $path)) { Fail "Không tìm thấy manifest $path. Keep-chain không tự deploy thay thế." }
    try { return (Get-Content $path -Raw | ConvertFrom-Json) }
    catch { Fail "Manifest không phải JSON hợp lệ: $path" }
}

function Set-PublicDeploymentEnvironment($Manifest, [string]$Id, [string]$RpcUrl) {
    foreach ($property in @('IdentitySBT', 'SSIRegistry', 'GatedService', 'chainId', 'genesisHash', 'deployer', 'transactions')) {
        if (-not $Manifest.PSObject.Properties.Name.Contains($property)) { Fail "Manifest thiếu trường $property." }
    }
    if ($Manifest.network -ne 'localhost' -or [string]$Manifest.chainId -ne '31337') { Fail 'Manifest không thuộc localhost chain ID 31337.' }
    foreach ($address in @($Manifest.IdentitySBT, $Manifest.SSIRegistry, $Manifest.GatedService)) {
        if ($address -notmatch '^0x[0-9a-fA-F]{40}$') { Fail 'Manifest có địa chỉ contract không hợp lệ.' }
    }
    $env:LOCAL_RPC_URL = $RpcUrl
    $env:SSI_DEPLOYMENT_ID = $Id
    $env:IDENTITY_SBT_ADDRESS = $Manifest.IdentitySBT
    $env:SSI_REGISTRY_ADDRESS = $Manifest.SSIRegistry
    $env:GATED_SERVICE_ADDRESS = $Manifest.GatedService
    $script:Run.deploymentId = $Id
    $script:Run.rpcUrl = $RpcUrl
    $script:Run.chainId = [string]$Manifest.chainId
    $script:Run.genesisHash = $Manifest.genesisHash
    $script:Run.manifest = $Manifest
}

function Invoke-Project([string]$Command, [string]$Label) {
    Info $Label
    Push-Location $Root
    try { Invoke-Expression $Command } finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { Fail "$Label thất bại." }
}

function Test-Deployment([string]$Id, [string]$Issuer) {
    # Existing helper calls loadDeployment(): verifies manifest genesis/receipts,
    # bytecode, Registry/SBT binding, Gate dependencies and admin roles.
    Invoke-Project 'npx hardhat run scripts/deploy-gated-service.ts --network localhost' 'Xác minh manifest, bytecode và liên kết contract'

    $abi = Join-Path $Root 'artifacts\contracts\SSIRegistry.sol\SSIRegistry.json'
    if (-not (Test-Path $abi)) { Fail 'Thiếu artifact SSIRegistry; chạy compile trước.' }
    # Keep this short-lived file under project root so Node resolves this project's
    # node_modules; it is removed in finally and never committed.
    $roleCheck = Join-Path $Root '.start-local-role-check.js'
    $script = @'
const fs=require("fs");
const {JsonRpcProvider,Contract}=require("ethers");
(async()=>{const a=JSON.parse(fs.readFileSync(process.env.SSI_REGISTRY_ABI,"utf8")).abi;const p=new JsonRpcProvider(process.env.LOCAL_RPC_URL);const r=new Contract(process.env.SSI_REGISTRY_ADDRESS,a,p);const role=await r.ISSUER_ROLE();if(!(await r.hasRole(role,process.env.SSI_ISSUER_ADDRESS))) throw new Error("ISSUER_ROLE missing");console.log("ISSUER_ROLE PASS");})().catch(e=>{console.error("ISSUER_ROLE verification failed");process.exit(1)});
'@
    $env:SSI_REGISTRY_ABI = $abi
    $env:SSI_ISSUER_ADDRESS = $Issuer
    try {
        Set-Content -Path $roleCheck -Value $script -Encoding UTF8
        Info 'Xác minh ISSUER_ROLE không thay đổi state'
        & node $roleCheck
        if ($LASTEXITCODE -ne 0) { Fail 'Xác minh ISSUER_ROLE không thay đổi state thất bại.' }
    } finally {
        Remove-Item $roleCheck -ErrorAction SilentlyContinue
        Remove-Item Env:SSI_REGISTRY_ABI -ErrorAction SilentlyContinue
        Remove-Item Env:SSI_ISSUER_ADDRESS -ErrorAction SilentlyContinue
    }
}

function Resolve-Kubo() {
    if (Test-Path $KuboPath) { return $KuboPath }
    $command = Get-Command ipfs -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    Fail 'Không tìm thấy Kubo/ipfs.exe. Cài Kubo hoặc truyền -KuboPath hợp lệ.'
}

function Kubo-Ready() {
    try {
        # PowerShell Invoke-RestMethod can receive a Kubo 403 despite the local
        # API accepting its canonical POST request. curl preserves that request.
        & curl.exe --silent --show-error --fail --request POST 'http://127.0.0.1:5001/api/v0/version' 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Start-KuboIfNeeded([hashtable]$Started) {
    if (Kubo-Ready) { Ok 'Kubo API đã chạy; giữ nguyên tiến trình hiện có.'; return }
    $binary = Resolve-Kubo
    $stdout = Join-Path $LogDirectory 'kubo.out.log'; $stderr = Join-Path $LogDirectory 'kubo.err.log'
    $process = Start-Process -FilePath $binary -ArgumentList 'daemon' -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Register-ManagedProcess $Started 'kubo' $process.Id 'kubo' $null
    $deadline = (Get-Date).AddSeconds(45)
    do { if (Kubo-Ready) { Ok 'Kubo API đã sẵn sàng.'; return }; Start-Sleep -Milliseconds 750 } while ((Get-Date) -lt $deadline)
    Fail "Kubo không sẵn sàng. Xem $stderr."
}

function Start-Dashboard([string]$Role, [string]$File, [int]$Port, [hashtable]$Started) {
    $owners = Port-Owner $Port
    if ($owners.Count -gt 0) {
        if ($Mode -eq 'Fresh') { Fail "$Role dashboard dùng cổng $Port. Fresh-chain không tái sử dụng dashboard cũ và không tự dừng tiến trình khác." }
        if (-not (Test-ReusableDashboard $Role $Port $Started)) {
            Fail "$Role dashboard đang dùng cổng $Port nhưng không được state file xác minh là dashboard SSI của Deployment ID $($script:Run.deploymentId). Hãy dừng tiến trình cũ hoặc chọn cổng khác."
        }
        Wait-Http "http://127.0.0.1:$Port/_stcore/health" "$Role dashboard đã xác minh" 5
        Info "$Role dashboard đã được xác minh cho Deployment ID $($script:Run.deploymentId); không khởi động trùng."
        return
    }
    $python = Join-Path $Root '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { Fail 'Thiếu .venv\Scripts\python.exe. Tạo venv và cài requirements.txt trước.' }
    $stdout = Join-Path $LogDirectory "$Role.out.log"; $stderr = Join-Path $LogDirectory "$Role.err.log"
    $arguments = @('-m','streamlit','run',$File,'--server.port',$Port,'--server.headless','true')
    $process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Register-ManagedProcess $Started "$Role-launcher" $process.Id 'dashboard-launcher' $Port
    Wait-Http "http://127.0.0.1:$Port/_stcore/health" "$Role dashboard"
    $listener = Port-Owner $Port
    if ($listener.Count -ne 1) { Fail "$Role dashboard tại cổng $Port không có PID listener duy nhất. Xem log tại $LogDirectory." }
    Register-ManagedProcess $Started $Role $listener[0] 'dashboard' $Port
    $Started.Remove("$Role-launcher") | Out-Null
    Save-State $Started
    Ok "$Role dashboard đã sẵn sàng tại http://127.0.0.1:$Port"
}

function Get-ProcessFingerprint([int]$ProcessId) {
    $details = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    if (-not $details -or -not $details.ExecutablePath -or -not $details.CommandLine -or -not $details.CreationDate) { return $null }
    return [ordered]@{
        pid = $ProcessId; executablePath = [System.IO.Path]::GetFullPath($details.ExecutablePath)
        # Store creation time as an ISO-8601 string. JSON number round-tripping can
        # lose precision for .NET ticks and would make a safe PID-reuse check fail.
        commandLine = $details.CommandLine; creationStamp = $details.CreationDate.ToUniversalTime().ToString('o')
    }
}

function Register-ManagedProcess([hashtable]$Started, [string]$Name, [int]$ProcessId, [string]$Kind, $Port) {
    $fingerprint = Get-ProcessFingerprint $ProcessId
    if (-not $fingerprint) { Fail "Không thể tạo fingerprint an toàn cho $Name (PID $ProcessId)." }
    $fingerprint.kind = $Kind; $fingerprint.port = $Port
    $fingerprint.deploymentId = $script:Run.deploymentId
    $fingerprint.chainId = $script:Run.chainId
    $fingerprint.genesisHash = $script:Run.genesisHash
    $Started[$Name] = $fingerprint
    Save-State $Started
}

function Refresh-ManagedProcessContext([hashtable]$Started) {
    foreach ($entry in $Started.Values) {
        $entry.deploymentId = $script:Run.deploymentId
        $entry.chainId = $script:Run.chainId
        $entry.genesisHash = $script:Run.genesisHash
    }
    Save-State $Started
}

function Save-State([hashtable]$Started) {
    $state = [ordered]@{
        version = 2; createdAt = (Get-Date).ToString('o'); root = $Root
        deploymentId = $script:Run.deploymentId; rpcUrl = $script:Run.rpcUrl
        chainId = $script:Run.chainId; genesisHash = $script:Run.genesisHash
        processes = $Started
        manifests = if ($script:Run.manifest) { @{ path = (Manifest-Path $script:Run.deploymentId); registry = $script:Run.manifest.SSIRegistry; sbt = $script:Run.manifest.IdentitySBT; gate = $script:Run.manifest.GatedService } } else { $null }
    }
    [System.IO.File]::WriteAllText($StateFile, ($state | ConvertTo-Json -Depth 5), [System.Text.UTF8Encoding]::new($false))
}

function Test-ManagedProcess($Entry, [string]$ProjectRoot) {
    if (-not $Entry -or -not $Entry.pid -or -not $Entry.executablePath -or -not $Entry.commandLine -or -not $Entry.creationStamp) { return $false }
    $current = Get-ProcessFingerprint ([int]$Entry.pid)
    if (-not $current) { return $false }
    # ConvertFrom-Json materializes ISO timestamps as DateTime on some PowerShell
    # versions, so normalize both sides before comparing the process fingerprint.
    $savedCreationStamp = ([DateTime]$Entry.creationStamp).ToUniversalTime().ToString('o')
    if ($current.executablePath -ine $Entry.executablePath -or $current.commandLine -cne $Entry.commandLine -or $current.creationStamp -cne $savedCreationStamp) { return $false }
    if ($Entry.kind -eq 'hardhat' -and $current.commandLine -notlike "*$ProjectRoot*") { return $false }
    if ($Entry.kind -eq 'dashboard') {
        $expectedPort = "--server.port $($Entry.port)"
        if ($current.commandLine -notmatch '(?i)-m\s+streamlit\s+run\s+app\\(holder|issuer|verifier)\.py' -or
            $current.commandLine -notlike "*$expectedPort*") { return $false }
    }
    return $true
}

function Read-State() {
    if (-not ([System.IO.File]::Exists($StateFile))) {
        return [pscustomobject]@{ status = 'Missing'; state = $null; reason = $null }
    }
    try {
        $raw = Get-Content -LiteralPath $StateFile -Raw -ErrorAction Stop
        if ([string]::IsNullOrWhiteSpace($raw)) { throw 'State JSON trống.' }
        $state = $raw | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return [pscustomobject]@{ status = 'Invalid'; state = $null; reason = 'JSON không đọc được hoặc bị hỏng.' }
    }
    if (-not $state) {
        return [pscustomobject]@{ status = 'Invalid'; state = $null; reason = 'State JSON không có đối tượng gốc.' }
    }
    $required = @('version', 'root', 'deploymentId', 'processes')
    $missing = @($required | Where-Object { -not $state.PSObject.Properties.Name.Contains($_) })
    foreach ($name in @('version', 'root', 'deploymentId')) {
        if ($state.PSObject.Properties.Name.Contains($name) -and [string]::IsNullOrWhiteSpace([string]$state.$name)) { $missing += $name }
    }
    if ($state.PSObject.Properties.Name.Contains('processes') -and $null -eq $state.processes) { $missing += 'processes' }
    $missing = @($missing | Select-Object -Unique)
    if ($missing.Count -gt 0) {
        return [pscustomobject]@{ status = 'Invalid'; state = $null; reason = "Thiếu trường bắt buộc: $($missing -join ', ')." }
    }
    if ([string]$state.version -ne '2') {
        return [pscustomobject]@{ status = 'Invalid'; state = $null; reason = "Phiên bản state không hỗ trợ: $($state.version)." }
    }
    if (-not (Test-StateRoot $state)) {
        return [pscustomobject]@{ status = 'Invalid'; state = $null; reason = 'State thuộc repository root khác.' }
    }
    $processValidation = Test-StateProcesses $state.processes
    if (-not $processValidation.valid) {
        return [pscustomobject]@{ status = 'Invalid'; state = $null; reason = $processValidation.reason }
    }
    return [pscustomobject]@{ status = 'Valid'; state = $state; reason = $null }
}

function Test-StateRoot($State) {
    if (-not $State -or -not $State.root) { return $false }
    try {
        return [System.IO.Path]::GetFullPath([string]$State.root).TrimEnd('\') -ieq
            [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    } catch { return $false }
}

function Test-StateProcesses($Processes) {
    # ConvertFrom-Json maps a JSON object to PSCustomObject. Arrays, scalar values
    # and null are deliberately rejected even when the JSON itself is syntactically valid.
    if ($Processes -isnot [pscustomobject]) {
        return [pscustomobject]@{ valid = $false; reason = 'Trường processes phải là JSON object.' }
    }
    $allowedKinds = @('hardhat-launcher', 'hardhat-child', 'hardhat', 'kubo', 'dashboard-launcher', 'dashboard')
    foreach ($property in $Processes.PSObject.Properties) {
        $name = [string]$property.Name
        $entry = $property.Value
        if ([string]::IsNullOrWhiteSpace($name) -or $entry -isnot [pscustomobject]) {
            return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' phải là JSON object." }
        }
        $required = @('pid', 'executablePath', 'commandLine', 'creationStamp', 'kind')
        foreach ($field in $required) {
            if (-not $entry.PSObject.Properties.Name.Contains($field) -or $null -eq $entry.$field) {
                return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' thiếu trường $field." }
            }
        }
        if ($entry.pid -isnot [byte] -and $entry.pid -isnot [int16] -and $entry.pid -isnot [int32] -and $entry.pid -isnot [int64] -and
            $entry.pid -isnot [uint16] -and $entry.pid -isnot [uint32] -and $entry.pid -isnot [uint64] -or [Int64]$entry.pid -le 0) {
            return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' có pid không phải số nguyên dương." }
        }
        foreach ($field in @('executablePath', 'commandLine')) {
            if ($entry.$field -isnot [string] -or [string]::IsNullOrWhiteSpace([string]$entry.$field)) {
                return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' có $field không phải chuỗi không rỗng." }
            }
        }
        try { $stamp = ([DateTime]$entry.creationStamp).ToUniversalTime() }
        catch { return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' có creationStamp không hợp lệ." } }
        if ($stamp -eq [DateTime]::MinValue) {
            return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' có creationStamp không hợp lệ." }
        }
        if ($entry.kind -isnot [string] -or $allowedKinds -notcontains $entry.kind) {
            return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' có kind không được hỗ trợ." }
        }
        $hasPort = $entry.PSObject.Properties.Name.Contains('port')
        $portIsValid = $hasPort -and ($entry.port -is [byte] -or $entry.port -is [int16] -or $entry.port -is [int32] -or $entry.port -is [int64] -or $entry.port -is [uint16] -or $entry.port -is [uint32] -or $entry.port -is [uint64]) -and [Int64]$entry.port -ge 1 -and [Int64]$entry.port -le 65535
        switch ($entry.kind) {
            'hardhat-launcher' { if ($name -ne 'hardhat-launcher' -or -not $portIsValid) { return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' không nhất quán với kind hardhat-launcher." } } }
            'hardhat' { if ($name -ne 'hardhat' -or -not $portIsValid) { return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' không nhất quán với kind hardhat." } } }
            'hardhat-child' { if ($name -notmatch '^hardhat-child-\d+$' -or ($hasPort -and $null -ne $entry.port)) { return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' không nhất quán với kind hardhat-child." } } }
            'kubo' { if ($name -ne 'kubo' -or ($hasPort -and $null -ne $entry.port)) { return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' không nhất quán với kind kubo." } } }
            'dashboard-launcher' { if ($name -notmatch '^(holder|issuer|verifier)-launcher$' -or -not $portIsValid) { return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' không nhất quán với kind dashboard-launcher." } } }
            'dashboard' { if ($name -notmatch '^(holder|issuer|verifier)$' -or -not $portIsValid) { return [pscustomobject]@{ valid = $false; reason = "Process entry '$name' không nhất quán với kind dashboard." } } }
        }
    }
    return [pscustomobject]@{ valid = $true; reason = $null }
}

function Get-StateProcessReview($State) {
    $review = [ordered]@{ valid = @{}; unresolved = @{}; stale = @{} }
    if (-not $State -or -not $State.processes) { return $review }
    foreach ($property in $State.processes.PSObject.Properties) {
        $entry = $property.Value
        $process = if ($entry.pid) { Get-Process -Id ([int]$entry.pid) -ErrorAction SilentlyContinue } else { $null }
        if (-not $process) { $review.stale[$property.Name] = $entry }
        elseif (Test-ManagedProcess $entry $Root) { $review.valid[$property.Name] = $entry }
        else { $review.unresolved[$property.Name] = $entry }
    }
    return $review
}

function Assert-StateCanStart($State, [string]$RequestedDeploymentId, [string]$RequestedMode) {
    if (-not $State) { return }
    if ($State.version -ne 2 -or -not (Test-StateRoot $State)) {
        Fail 'State file không thuộc repository hiện tại hoặc không hợp lệ; script không ghi đè để tránh mất quyền quản lý tiến trình cũ.'
    }
    $review = Get-StateProcessReview $State
    $liveNames = @($review.valid.Keys) + @($review.unresolved.Keys)
    if ($liveNames.Count -eq 0) { return }

    $sameDeployment = $RequestedMode -eq 'Keep' -and $State.deploymentId -eq $RequestedDeploymentId
    if ($sameDeployment -and $review.unresolved.Count -eq 0) { return }

    $details = @($liveNames | ForEach-Object { "$($_) (PID $($State.processes.$_.pid))" }) -join ', '
    if ($sameDeployment) {
        Fail "State hiện có tiến trình chưa xác minh được: $details. Không ghi đè state; hãy kiểm tra thủ công hoặc chạy -Stop."
    }
    Fail "Phiên Deployment ID $($State.deploymentId) vẫn còn tiến trình: $details. Không ghi đè state; hãy chạy .\\start-local.ps1 -Stop hoặc xử lý phiên cũ trước."
}

function Save-RemainingState($State, [hashtable]$Remaining) {
    $saved = [ordered]@{
        version = 2; createdAt = (Get-Date).ToString('o'); root = $State.root
        deploymentId = $State.deploymentId; rpcUrl = $State.rpcUrl
        chainId = $State.chainId; genesisHash = $State.genesisHash
        processes = $Remaining; manifests = $State.manifests
    }
    [System.IO.File]::WriteAllText($StateFile, ($saved | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))
}

function Get-ProcessObservation([int]$ProcessId) {
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        return [pscustomobject]@{ status = 'Present'; process = $process }
    } catch {
        if ($_.CategoryInfo.Category -eq [System.Management.Automation.ErrorCategory]::ObjectNotFound) {
            return [pscustomobject]@{ status = 'Missing'; process = $null }
        }
        return [pscustomobject]@{ status = 'Unknown'; process = $null }
    }
}

function Wait-ProcessStopped([int]$ProcessId, [int]$TimeoutSeconds = 5) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $observation = Get-ProcessObservation $ProcessId
        if ($observation.status -ne 'Present') { return $observation.status }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    return (Get-ProcessObservation $ProcessId).status
}

function Get-OwnedProcessState($State) {
    $owned = @{}
    if (-not $State -or $State.version -ne 2 -or -not (Test-StateRoot $State) -or -not $State.processes) { return $owned }
    foreach ($entry in $State.processes.PSObject.Properties) {
        if (Test-ManagedProcess $entry.Value $Root) { $owned[$entry.Name] = $entry.Value }
    }
    return $owned
}

function Test-ReusableDashboard([string]$Role, [int]$Port, [hashtable]$Started) {
    if (-not $Started.ContainsKey($Role)) { return $false }
    $entry = $Started[$Role]
    return $entry.kind -eq 'dashboard' -and [int]$entry.port -eq $Port -and
        $entry.deploymentId -eq $script:Run.deploymentId -and $entry.chainId -eq $script:Run.chainId -and
        $entry.genesisHash -eq $script:Run.genesisHash -and (Test-ManagedProcess $entry $Root)
}

function Stop-StartedProcesses() {
    $stateResult = Read-State
    if ($stateResult.status -eq 'Missing') { Info 'Không có state file của start-local.ps1 để dừng.'; return }
    if ($stateResult.status -ne 'Valid') {
        Info "State file không hợp lệ ($($stateResult.reason)); không dừng tiến trình nào và không sửa state. Hãy kiểm tra thủ công các PID trước khi xử lý file."
        return
    }
    $state = $stateResult.state
    $remaining = @{}
    foreach ($entry in $state.processes.PSObject.Properties) {
        $processId = [int]$entry.Value.pid
        $before = Get-ProcessObservation $processId
        if ($before.status -eq 'Missing') {
            Info "Loại bỏ bản ghi $($entry.Name) (PID $processId) vì tiến trình không còn tồn tại."
            continue
        }
        if ($before.status -eq 'Unknown') {
            $remaining[$entry.Name] = $entry.Value
            Info "Giữ bản ghi $($entry.Name) (PID $processId): không xác minh được trạng thái tiến trình."
            continue
        }
        # PID reuse is rejected by executable path, exact command line and creation time.
        if (Test-ManagedProcess $entry.Value $Root) {
            try {
                Stop-Process -Id $processId -ErrorAction Stop
                $afterStop = Wait-ProcessStopped $processId
                if ($afterStop -eq 'Missing') {
                    Info "Đã xác nhận dừng tiến trình $($entry.Name) do script khởi tạo (PID $processId)."
                } elseif ($afterStop -eq 'Present' -and (Test-ManagedProcess $entry.Value $Root)) {
                    $remaining[$entry.Name] = $entry.Value
                    Info "Giữ bản ghi $($entry.Name) (PID $processId): process vẫn chạy sau timeout dừng."
                } else {
                    $remaining[$entry.Name] = $entry.Value
                    Info "Giữ bản ghi $($entry.Name) (PID $processId): không xác minh an toàn việc dừng process."
                }
            } catch {
                $remaining[$entry.Name] = $entry.Value
                Info "Giữ bản ghi $($entry.Name) (PID $processId): Stop-Process thất bại; cần xử lý lại."
            }
        } else {
            $remaining[$entry.Name] = $entry.Value
            Info "Giữ bản ghi $($entry.Name) (PID $processId): fingerprint không khớp; không xác minh được quyền sở hữu."
        }
    }
    if ($remaining.Count -eq 0) {
        if ([System.IO.File]::Exists($StateFile)) { [System.IO.File]::Delete($StateFile) }
    } else {
        Save-RemainingState $state $remaining
        Info "State vẫn được giữ cho: $($remaining.Keys -join ', ')."
    }
}

if ($Stop) { Stop-StartedProcesses; exit 0 }

if (-not $Mode) {
    Write-Host "========================================"
    Write-Host "       SSI PROJECT - LOCAL STARTUP"
    Write-Host "========================================"
    Write-Host "1. Fresh-chain - Tạo blockchain mới"
    Write-Host "2. Keep-chain  - Sử dụng blockchain hiện tại"
    Write-Host "0. Exit        - Thoát"
    switch (Read-Host 'Vui lòng chọn chế độ') {
        '1' { $Mode = 'Fresh' }
        '2' { $Mode = 'Keep' }
        '0' { exit 0 }
        default { Fail 'Lựa chọn không hợp lệ.' }
    }
}

if ($Mode -eq 'Keep' -and -not $DeploymentId) { $DeploymentId = Read-Host 'Nhập Deployment ID cần giữ (bắt buộc)' }

Push-Location $Root
try {
    Require-Command 'node'; Require-Command 'npm'; Require-Command 'python'
    if (-not (Test-Path (Join-Path $Root 'node_modules'))) { Fail 'Thiếu node_modules. Chạy npm install trước.' }
    if (-not (Test-Path (Join-Path $Root '.venv\Scripts\python.exe'))) { Fail 'Thiếu Python venv. Tạo .venv và cài requirements.txt trước.' }
    New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
    $issuer = Require-IssuerAddress
    $rpcUrl = "http://127.0.0.1:$RpcPort"
    $priorStateResult = Read-State
    if ($priorStateResult.status -eq 'Invalid') {
        Fail "State file không hợp lệ ($($priorStateResult.reason)); không ghi đè state. Hãy xác định các tiến trình còn chạy trước khi sửa hoặc di chuyển file thủ công."
    }
    $priorState = $priorStateResult.state
    $started = @{}

    # One state file intentionally represents one managed session. Never overwrite
    # live process records from another deployment (or records we cannot verify).
    Assert-StateCanStart $priorState $DeploymentId $Mode

    if ($Mode -eq 'Fresh') {
        Assert-Port-Free $RpcPort 'Hardhat node'
        Assert-Port-Free $HolderPort 'Holder dashboard'; Assert-Port-Free $IssuerPort 'Issuer dashboard'; Assert-Port-Free $VerifierPort 'Verifier dashboard'
        Invoke-Project 'npm run compile' 'Compile contracts'
        $DeploymentId = New-DeploymentId
        $script:Run.deploymentId = $DeploymentId
        $script:Run.rpcUrl = $rpcUrl
        $nodeOut = Join-Path $LogDirectory 'hardhat.out.log'; $nodeErr = Join-Path $LogDirectory 'hardhat.err.log'
        $node = Start-Process -FilePath 'npx.cmd' -ArgumentList @('hardhat','node','--port',$RpcPort) -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $nodeOut -RedirectStandardError $nodeErr
        # Persist the launcher immediately. On Windows npx.cmd may spawn a child
        # Node process, so Wait-Rpc also records the real port listener when found.
        Register-ManagedProcess $started 'hardhat-launcher' $node.Id 'hardhat-launcher' $RpcPort
        Wait-Rpc $rpcUrl $RpcPort $started | Out-Null
        $nodeOwners = Port-Owner $RpcPort
        if ($nodeOwners.Count -ne 1) { Fail "Không xác định được duy nhất PID Hardhat ở cổng $RpcPort." }
        Register-ManagedProcess $started 'hardhat' $nodeOwners[0] 'hardhat' $RpcPort
        $env:LOCAL_RPC_URL = $rpcUrl; $env:SSI_DEPLOYMENT_ID = $DeploymentId; $env:ISSUER_ADDRESS = $issuer
        Invoke-Project 'npm run deploy:local' 'Deploy IdentitySBT, SSIRegistry, Registry binding và GatedService'
        $manifest = Read-Manifest $DeploymentId
        Set-PublicDeploymentEnvironment $manifest $DeploymentId $rpcUrl
        Refresh-ManagedProcessContext $started
        Invoke-Project 'npm run roles:local' 'Cấp ISSUER_ROLE'
        Test-Deployment $DeploymentId $issuer
    } else {
        if ((Get-RpcChainId $rpcUrl) -ne 31337) { Fail "Keep-chain cần RPC đang chạy tại $rpcUrl với chain ID 31337; script không tự chuyển sang Fresh-chain." }
        $manifest = Read-Manifest $DeploymentId
        Set-PublicDeploymentEnvironment $manifest $DeploymentId $rpcUrl
        if ($priorState -and $priorState.deploymentId -eq $DeploymentId -and $priorState.rpcUrl -eq $rpcUrl -and
            $priorState.chainId -eq $script:Run.chainId -and $priorState.genesisHash -eq $script:Run.genesisHash) {
            $started = Get-OwnedProcessState $priorState
        }
        Refresh-ManagedProcessContext $started
        Test-Deployment $DeploymentId $issuer
        Ok 'Keep-chain đã được xác minh; không deploy hoặc gửi transaction.'
    }

    Info 'Kiểm tra Kubo'
    Start-KuboIfNeeded -Started $started
    Info 'Khởi động hoặc kiểm tra dashboard Holder'
    Start-Dashboard 'holder' 'app\holder.py' $HolderPort $started
    Info 'Khởi động hoặc kiểm tra dashboard Issuer'
    Start-Dashboard 'issuer' 'app\issuer.py' $IssuerPort $started
    Info 'Khởi động hoặc kiểm tra dashboard Verifier'
    Start-Dashboard 'verifier' 'app\verifier.py' $VerifierPort $started
    Save-State $started

    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host 'SSI local environment is ready' -ForegroundColor Green
    Write-Host "Chain ID: $($manifest.chainId) | Deployment ID: $DeploymentId"
    Write-Host "IdentitySBT: $($manifest.IdentitySBT)"
    Write-Host "SSIRegistry: $($manifest.SSIRegistry)"
    Write-Host "GatedService: $($manifest.GatedService)"
    Write-Host "Holder: http://127.0.0.1:$HolderPort | Issuer: http://127.0.0.1:$IssuerPort | Verifier: http://127.0.0.1:$VerifierPort"
    Write-Host "Manifest: $(Manifest-Path $DeploymentId)"
    Write-Host "Dừng các tiến trình do script khởi tạo: .\start-local.ps1 -Stop"
} catch {
    Write-Error $_.Exception.Message
    if ($Mode -eq 'Fresh') { Write-Host 'Fresh-chain đã dừng khi lỗi; manifest chỉ được publish sau khi deploy verification PASS.' -ForegroundColor Yellow }
    exit 1
} finally { Pop-Location }
