param(
    [switch]$Launch,
    [switch]$Visible,
    [switch]$QuitAfterCheck
)

$ErrorActionPreference = "Stop"

$registered = Test-Path -LiteralPath "Registry::HKEY_CLASSES_ROOT\SldWorks.Application"
if (-not $registered) {
    Write-Output "SOLIDWORKS_COM_REGISTERED=False"
    exit 2
}

Write-Output "SOLIDWORKS_COM_REGISTERED=True"

$clsidKey = "Registry::HKEY_CLASSES_ROOT\SldWorks.Application\CLSID"
try {
    $clsid = (Get-ItemProperty -LiteralPath $clsidKey)."(default)"
    Write-Output ("SOLIDWORKS_CLSID={0}" -f $clsid)
    $serverKey = "Registry::HKEY_CLASSES_ROOT\CLSID\$clsid\LocalServer32"
    $server = (Get-ItemProperty -LiteralPath $serverKey)."(default)"
    Write-Output ("SOLIDWORKS_SERVER={0}" -f $server)
} catch {
    Write-Output ("SOLIDWORKS_SERVER=UNKNOWN; ERROR={0}" -f $_.Exception.Message)
}

if (-not $Launch) {
    exit 0
}

$swApp = New-Object -ComObject SldWorks.Application
try {
    $swApp.Visible = [bool]$Visible
    Write-Output ("SOLIDWORKS_VISIBLE_SET={0}" -f ([bool]$Visible))
} catch {
    Write-Output ("SOLIDWORKS_VISIBLE_SET=False; ERROR={0}" -f $_.Exception.Message)
}

$revision = $null
try {
    $revision = $swApp.RevisionNumber()
} catch {
    $revision = "UNKNOWN; ERROR=$($_.Exception.Message)"
}

Write-Output ("SOLIDWORKS_REVISION={0}" -f $revision)
Write-Output "SOLIDWORKS_LAUNCHED=True"

if ($QuitAfterCheck) {
    try {
        $swApp.ExitApp()
        Write-Output "SOLIDWORKS_EXIT_REQUESTED=True"
    } catch {
        Write-Output ("SOLIDWORKS_EXIT_REQUESTED=False; ERROR={0}" -f $_.Exception.Message)
    }
}
