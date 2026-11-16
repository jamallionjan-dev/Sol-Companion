param(
    [Parameter(Mandatory = $true)][string]$JavaPath,
    [Parameter(Mandatory = $true)][string]$ArgsFile,
    [Parameter(Mandatory = $true)][string]$JarPath,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][string]$ProfileRoot
)

$ErrorActionPreference = 'Stop'
$testRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$evidenceDir = Join-Path $testRoot (Join-Path 'runtime-evidence' $stamp)
New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null
$stdoutPath = Join-Path $evidenceDir 'stdout.log'
$stderrPath = Join-Path $evidenceDir 'stderr.log'
$metadataPath = Join-Path $evidenceDir 'launch_metadata.txt'
$statusPath = Join-Path $evidenceDir 'process_status.txt'
$debugTailPath = Join-Path $evidenceDir 'debuglog_tail_latest.txt'
$processLogPath = Join-Path $evidenceDir 'process_timeline.log'
$gameRoot = $WorkingDirectory.TrimEnd('\')

function Get-PzRuntimeProcesses {
    @(Get-Process -Name java, javaw -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and $_.Path.StartsWith((Join-Path $gameRoot 'jre64\bin'), [StringComparison]::OrdinalIgnoreCase) })
}

function Write-DebugTail {
    $logsRoot = Join-Path $ProfileRoot 'Zomboid\Logs'
    $candidate = Get-ChildItem -LiteralPath $logsRoot -Recurse -File -Filter '*DebugLog.txt' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($candidate) {
        $tail = Get-Content -LiteralPath $candidate.FullName -Tail 600 -ErrorAction SilentlyContinue
        @("SOURCE=$($candidate.FullName)", "LAST_WRITE=$($candidate.LastWriteTime.ToString('o'))", '') + $tail |
            Set-Content -LiteralPath $debugTailPath -Encoding UTF8
    }
}

function Write-Status([string]$State, [int]$PidValue, [Nullable[int]]$ExitCodeValue, [int]$Count) {
    @(
        "UPDATED=$(Get-Date -Format o)",
        "STATE=$State",
        "PID=$PidValue",
        "EXIT_CODE=$(if ($null -eq $ExitCodeValue) { 'unknown' } else { $ExitCodeValue })",
        "PZ_COUNT=$Count",
        "EVIDENCE_DIR=$evidenceDir"
    ) | Set-Content -LiteralPath $statusPath -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $JavaPath -PathType Leaf)) { throw "Java executable missing: $JavaPath" }
if (-not (Test-Path -LiteralPath $ArgsFile -PathType Leaf)) { throw "Args file missing: $ArgsFile" }
if (-not (Test-Path -LiteralPath $JarPath -PathType Leaf)) { throw "Test JAR missing: $JarPath" }
if (-not (Test-Path -LiteralPath $WorkingDirectory -PathType Container)) { throw "Working directory missing: $WorkingDirectory" }

$preProcesses = Get-PzRuntimeProcesses
$preCount = $preProcesses.Count
$jarHash = (Get-FileHash -LiteralPath $JarPath -Algorithm SHA256).Hash
$argsHash = (Get-FileHash -LiteralPath $ArgsFile -Algorithm SHA256).Hash
$javaVersion = (Get-Item -LiteralPath $JavaPath).VersionInfo.FileVersion
$metadata = @(
    'PROCEDURE=Project Zomboid bundled Java executable with the recovered test args file',
    "CREATED=$(Get-Date -Format o)",
    "JAVA=$JavaPath",
    "JAVA_FILE_VERSION=$javaVersion",
    "ARGS_FILE=$ArgsFile",
    "ARGS_SHA256=$argsHash",
    "JAR=$JarPath",
    "JAR_SHA256=$jarHash",
    "WORKING_DIRECTORY=$WorkingDirectory",
    "PROFILE_ROOT=$ProfileRoot",
    "INTENDED_COMMAND_LINE=`"$JavaPath`" @`"$ArgsFile`"",
    "PRELAUNCH_PZ_COUNT=$preCount",
    "PRELAUNCH_PIDS=$(($preProcesses | ForEach-Object Id) -join ',')"
)
$metadata | Set-Content -LiteralPath $metadataPath -Encoding UTF8
if ($preCount -ne 0) {
    Write-Status 'ABORTED_PRELAUNCH_PZ_PRESENT' 0 $null $preCount
    throw "Launch aborted: PZ_COUNT=$preCount; no process started."
}

$proc = Start-Process -FilePath $JavaPath -ArgumentList ('@' + $ArgsFile) -WorkingDirectory $WorkingDirectory `
    -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -WindowStyle Normal
$pidValue = $proc.Id
$startedAt = $proc.StartTime.ToString('o')
Add-Content -LiteralPath $metadataPath -Value @("PID=$pidValue", "PROCESS_START_TIME=$startedAt", "STARTED_COMMAND_LINE=`"$JavaPath`" @`"$ArgsFile`"") -Encoding UTF8
"$(Get-Date -Format o) STARTED PID=$pidValue PZ_COUNT=$((Get-PzRuntimeProcesses).Count)" | Add-Content -LiteralPath $processLogPath -Encoding UTF8

$readyLogged = $false
while (-not $proc.HasExited) {
    Start-Sleep -Seconds 3
    $proc.Refresh()
    $count = (Get-PzRuntimeProcesses).Count
    $state = if ($proc.HasExited) { 'EXITED' } else { 'RUNNING' }
    Write-Status $state $pidValue $null $count
    Write-DebugTail
    if (-not $readyLogged -and (Select-String -LiteralPath $stdoutPath -Pattern '\[SolNativeBridge\] READY|Runtime command channel READY' -Quiet -ErrorAction SilentlyContinue)) {
        $readyLogged = $true
        "$(Get-Date -Format o) BRIDGE_OR_HARNESS_READY PZ_COUNT=$count" | Add-Content -LiteralPath $processLogPath -Encoding UTF8
    }
    "$(Get-Date -Format o) PID=$pidValue STATE=$state PZ_COUNT=$count" | Add-Content -LiteralPath $processLogPath -Encoding UTF8
}

$proc.WaitForExit()
$exitCode = $proc.ExitCode
$postCount = (Get-PzRuntimeProcesses).Count
Write-DebugTail
Write-Status 'EXITED' $pidValue $exitCode $postCount
@(
    "$(Get-Date -Format o) EXITED PID=$pidValue EXIT_CODE=$exitCode PZ_COUNT=$postCount",
    "READY_MARKER_OBSERVED=$readyLogged"
) | Add-Content -LiteralPath $processLogPath -Encoding UTF8
if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Tail 300 | Set-Content -LiteralPath (Join-Path $evidenceDir 'stdout_tail.txt') -Encoding UTF8 }
if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Tail 300 | Set-Content -LiteralPath (Join-Path $evidenceDir 'stderr_tail.txt') -Encoding UTF8 }
Write-Output "EVIDENCE_DIR=$evidenceDir"
Write-Output "PID=$pidValue EXIT_CODE=$exitCode PZ_COUNT_AFTER_EXIT=$postCount READY=$readyLogged"
