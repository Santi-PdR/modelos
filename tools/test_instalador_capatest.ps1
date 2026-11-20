# Exercise the real CI-built JAR in disposable instances, not the user's mods.
param(
    [Parameter(Mandatory = $true)][string]$Installer,
    [Parameter(Mandatory = $true)][string]$Jar
)
$ErrorActionPreference = 'Stop'

function Assert-Check([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

$jarInfo = Get-Item -LiteralPath $Jar
$jarHash = (Get-FileHash -LiteralPath $jarInfo.FullName).Hash
$root = Join-Path ([IO.Path]::GetTempPath()) ('capatest test [fixture] ' + [guid]::NewGuid().ToString('N'))
$mods = Join-Path $root 'mods'
$backup = Join-Path $root 'capatest-respaldos'
$old = Join-Path $mods 'capatest-1.67.12.jar'
$next = Join-Path $mods $jarInfo.Name
$other = Join-Path $mods 'otro-mod.jar'
try {
    [void][IO.Directory]::CreateDirectory($mods)
    [IO.File]::WriteAllText($old, 'old cape')
    [IO.File]::WriteAllText($next, 'wrong build with the same name')
    [IO.File]::WriteAllText($other, 'unrelated mod')
    $otherHash = (Get-FileHash -LiteralPath $other).Hash

    # A bad download aborts before creating a backup or moving any mod.
    $bad = Join-Path $root $jarInfo.Name
    [IO.File]::WriteAllText($bad, 'damaged download')
    $rejected = $false
    try { & $Installer -Jar $bad -ModsDir $mods -Confirm:$false }
    catch {
        if ($_.Exception.Message -notlike 'SHA-256 distinto*') { throw }
        $rejected = $true
    }
    Assert-Check $rejected 'The corrupted download was not rejected.'
    & $Installer -Jar $jarInfo.FullName -ModsDir $mods -WhatIf
    Assert-Check (-not (Test-Path -LiteralPath $backup)) 'Verification/dry run created a backup.'
    Assert-Check (([IO.File]::ReadAllText($old) -eq 'old cape') -and
        ([IO.File]::ReadAllText($next) -eq 'wrong build with the same name')) 'Dry run changed installed files.'

    & $Installer -Jar $jarInfo.FullName -ModsDir $mods -Confirm:$false
    Assert-Check ((Get-FileHash -LiteralPath $next).Hash -eq $jarHash) 'Installed JAR is not the CI build.'
    Assert-Check (-not [IO.File]::Exists($old)) 'The old cape is still in mods.'
    $saves = @(Get-ChildItem -LiteralPath $backup -Directory)
    Assert-Check ($saves.Count -eq 1) 'Expected exactly one backup folder.'
    Assert-Check (([IO.File]::ReadAllText((Join-Path $saves[0].FullName 'capatest-1.67.12.jar')) -eq 'old cape') -and
        ([IO.File]::ReadAllText((Join-Path $saves[0].FullName $jarInfo.Name)) -eq 'wrong build with the same name')) 'Old JARs were not backed up byte for byte.'
    Assert-Check ((Get-FileHash -LiteralPath $other).Hash -eq $otherHash) 'An unrelated mod changed.'
    & $Installer -Jar $jarInfo.FullName -ModsDir $mods -Confirm:$false
    Assert-Check (@(Get-ChildItem -LiteralPath $backup -Directory).Count -eq 1) 'A second install replaced the backup.'
    Assert-Check (@(Get-ChildItem -LiteralPath $mods -Force -File).Count -eq 2) 'Staging or duplicate files were left in mods.'

    # Make the final rename fail after moving an old JAR; it must be restored.
    $blocked = Join-Path (Join-Path $root 'blocked') 'mods'
    [void][IO.Directory]::CreateDirectory((Join-Path $blocked $jarInfo.Name))
    $atRisk = Join-Path $blocked 'capatest-1.67.12.jar'
    [IO.File]::WriteAllText($atRisk, 'restore me')
    $rejected = $false
    try { & $Installer -Jar $jarInfo.FullName -ModsDir $blocked -Confirm:$false }
    catch {
        if ($_.Exception -isnot [Management.Automation.MethodInvocationException] -or
                ($_.Exception.InnerException -isnot [IO.IOException] -and
                 $_.Exception.InnerException -isnot [UnauthorizedAccessException])) { throw }
        $rejected = $true
    }
    $restored = @(Get-ChildItem -LiteralPath (Join-Path (Split-Path $blocked -Parent) 'capatest-respaldos') -Directory)
    Assert-Check ($restored.Count -eq 1) 'The failure did not occur after creating the backup.'
    Assert-Check ($rejected -and [IO.File]::ReadAllText($atRisk) -eq 'restore me') 'A blocked install did not restore the old cape.'
    Assert-Check (@(Get-ChildItem -LiteralPath $blocked -Force -File).Count -eq 1) 'A blocked install left staging files.'
    Write-Host 'PASS: SHA-256, WhatIf, backups, unrelated mods, repeat install and rollback.'
} finally {
    if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
}
