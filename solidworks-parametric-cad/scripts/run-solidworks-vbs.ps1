param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath,

    [string]$WorkingDirectory = (Get-Location).Path,

    [string]$LogPath = "",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArguments = @()
)

$ErrorActionPreference = "Stop"

$resolvedScript = (Resolve-Path -LiteralPath $ScriptPath).Path
$resolvedWorkingDirectory = (Resolve-Path -LiteralPath $WorkingDirectory).Path
$validatorPath = Join-Path $PSScriptRoot "validate-solidworks-vbs.ps1"
$driverLibraryPath = Join-Path $PSScriptRoot "lib\solidworks-com-driver.vbs"

if ($LogPath -eq "") {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $LogPath = Join-Path $resolvedWorkingDirectory ("solidworks_vbs_{0}.log" -f $stamp)
} elseif (-not [System.IO.Path]::IsPathRooted($LogPath)) {
    $LogPath = Join-Path (Get-Location).Path $LogPath
}

# Preserve the runtime log even when the caller supplies a new output path.
# This prevents a missing log directory from hiding the SolidWorks error.
$logDirectory = Split-Path -Path $LogPath -Parent
if (-not [string]::IsNullOrEmpty($logDirectory) -and -not (Test-Path -LiteralPath $logDirectory)) {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

$existingCscript = @(Get-Process -Name cscript -ErrorAction SilentlyContinue)
if ($existingCscript.Count -gt 0) {
    $pids = ($existingCscript | ForEach-Object { $_.Id }) -join ","
    $runError = "RUN_ERROR=CSCRIPT_ALREADY_RUNNING|COUNT={0}|PIDS={1}" -f $existingCscript.Count, $pids
    Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value $runError
    Write-Output $runError
    Write-Output ("LOG_PATH={0}" -f $LogPath)
    throw "Refusing to run SolidWorks VBScript while another cscript.exe is active."
}

$solidWorksProcesses = @(Get-Process -Name SLDWORKS -ErrorAction SilentlyContinue)
if ($solidWorksProcesses.Count -gt 1) {
    $pids = ($solidWorksProcesses | ForEach-Object { $_.Id }) -join ","
    $runError = "RUN_ERROR=MULTIPLE_SOLIDWORKS_INSTANCES|COUNT={0}|PIDS={1}" -f $solidWorksProcesses.Count, $pids
    Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value $runError
    Write-Output $runError
    Write-Output ("LOG_PATH={0}" -f $LogPath)
    throw "Refusing to run SolidWorks VBScript with multiple SLDWORKS.exe instances."
}

Push-Location $resolvedWorkingDirectory
$runErrorLogged = $false
try {
    try {
        & $validatorPath -ScriptPath $resolvedScript
        if (Test-Path -LiteralPath $driverLibraryPath) {
            & $validatorPath -ScriptPath $driverLibraryPath -Kind library
        }
        Write-Output ("RUN_VBS={0}" -f $resolvedScript) | Tee-Object -FilePath $LogPath
        Write-Output ("WORKING_DIRECTORY={0}" -f $resolvedWorkingDirectory) | Tee-Object -FilePath $LogPath -Append
        Write-Output ("SCRIPT_ARGUMENT_COUNT={0}" -f $ScriptArguments.Count) | Tee-Object -FilePath $LogPath -Append
        & cscript //nologo $resolvedScript @ScriptArguments 2>&1 | Tee-Object -FilePath $LogPath -Append
        $scriptExitCode = $LASTEXITCODE
        Write-Output ("CSCRIPT_EXIT_CODE={0}" -f $scriptExitCode) | Tee-Object -FilePath $LogPath -Append
        if ($scriptExitCode -ne 0) {
            $runError = "RUN_ERROR=SolidWorks VBScript exited with code $scriptExitCode"
            Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value $runError
            Write-Output $runError
            Write-Output ("LOG_PATH={0}" -f $LogPath)
            $runErrorLogged = $true
            throw "SolidWorks VBScript exited with code $scriptExitCode"
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
