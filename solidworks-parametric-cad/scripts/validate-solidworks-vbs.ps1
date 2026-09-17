param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath,

    [ValidateSet("auto", "formal", "qualification", "library", "baseline")]
    [string]$Kind = "auto"
)

$ErrorActionPreference = "Stop"

$resolvedScript = (Resolve-Path -LiteralPath $ScriptPath).Path
$text = Get-Content -LiteralPath $resolvedScript -Raw

if ($Kind -eq "auto") {
    if ($text -match "SW_SCRIPT_KIND=(formal|qualification|library|baseline)") {
        $Kind = $Matches[1]
    } else {
        $Kind = "formal"
    }
}

$errors = [System.Collections.Generic.List[string]]::new()

function Add-ForbiddenMatch {
    param(
        [string]$Pattern,
        [string]$Message
    )
    if ($text -match $Pattern) {
        $errors.Add($Message)
    }
}

Add-ForbiddenMatch -Pattern '(?i)Shell\.Run|WScript\.Shell' -Message "child process orchestration is forbidden"
Add-ForbiddenMatch -Pattern '(?i)\bcscript(\.exe)?\b' -Message "nested cscript invocation is forbidden"

$createCount = ([regex]::Matches($text, '(?i)CreateObject\(\s*"SldWorks\.Application"\s*\)')).Count
if ($Kind -eq "library" -or $Kind -eq "baseline") {
    if ($createCount -ne 1) {
        $errors.Add("$Kind script must contain exactly one SolidWorks CreateObject fallback")
    }
} elseif ($createCount -gt 0) {
    $errors.Add("entry script must attach through the shared driver instead of creating SolidWorks directly")
}

if ($Kind -eq "formal") {
    Add-ForbiddenMatch -Pattern '(?i)sgFIXED|\.ConstrainAll\s*\(|\.FullyDefineSketch\s*\(' -Message "formal scripts cannot blanket-fix or auto-define sketches"
    Add-ForbiddenMatch -Pattern '(?i)\.FeatureExtrusion2\s*\(|\.FeatureCut3\s*\(|\.InsertProtrusionSwept\d*\s*\(|\.InsertCutSwept\d*\s*\(' -Message "formal scripts must call calibrated driver helpers for fragile feature APIs"
    Add-ForbiddenMatch -Pattern '(?i)\.CreateCircleByRadius\s*\(' -Message "formal scripts must create face-plane circles through DriverCircleLocal"
}

if ($errors.Count -gt 0) {
    foreach ($item in $errors) {
        Write-Output ("STATIC_CHECK_ERROR={0}" -f $item)
    }
    throw "SolidWorks VBScript static validation failed"
}

Write-Output ("STATIC_CHECK_PASS={0}|KIND={1}" -f $resolvedScript, $Kind)
