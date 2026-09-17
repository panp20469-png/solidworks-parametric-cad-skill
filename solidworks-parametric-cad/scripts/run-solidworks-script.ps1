param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath,

    [string]$WorkingDirectory = (Get-Location).Path,

    [string]$LogPath = ""
)

$ErrorActionPreference = "Stop"

$resolvedScript = (Resolve-Path -LiteralPath $ScriptPath).Path
$resolvedWorkingDirectory = (Resolve-Path -LiteralPath $WorkingDirectory).Path

if ($LogPath -eq "") {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $LogPath = Join-Path $resolvedWorkingDirectory ("solidworks_automation_{0}.log" -f $stamp)
} elseif (-not [System.IO.Path]::IsPathRooted($LogPath)) {
    $LogPath = Join-Path (Get-Location).Path $LogPath
}

# Create the caller-supplied log directory before invoking the wrapped script.
$logDirectory = Split-Path -Path $LogPath -Parent
if (-not [string]::IsNullOrEmpty($logDirectory) -and -not (Test-Path -LiteralPath $logDirectory)) {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

Push-Location $resolvedWorkingDirectory
$runErrorLogged = $false
try {
    try {
        Write-Output ("RUN_SCRIPT={0}" -f $resolvedScript) | Tee-Object -FilePath $LogPath
        Write-Output ("WORKING_DIRECTORY={0}" -f $resolvedWorkingDirectory) | Tee-Object -FilePath $LogPath -Append
        & powershell -NoProfile -ExecutionPolicy Bypass -File $resolvedScript 2>&1 | Tee-Object -FilePath $LogPath -Append
        $scriptExitCode = $LASTEXITCODE
        Write-Output ("POWERSHELL_EXIT_CODE={0}" -f $scriptExitCode) | Tee-Object -FilePath $LogPath -Append
        if ($scriptExitCode -ne 0) {
            $runError = "RUN_ERROR=SolidWorks automation script exited with code $scriptExitCode"
            Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value $runError
            Write-Output $runError
            Write-Output ("LOG_PATH={0}" -f $LogPath)
            $runErrorLogged = $true
            throw "SolidWorks automation script exited with code $scriptExitCode"
        }
        Write-Output ("LOG_PATH={0}" -f $LogPath)
    } catch {
        # Echo LOG_PATH even when the wrapped script fails.
        if (-not $runErrorLogged) {
            $runError = "RUN_ERROR=$($_.Exception.Message)"
            Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value $runError
            Write-Output $runError
            Write-Output ("LOG_PATH={0}" -f $LogPath)
        }
        throw
    }
} finally {
    Pop-Location
}
