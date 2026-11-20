# Run with Minecraft closed. The input is the extracted JAR, not the Actions ZIP.
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Jar,
    [string]$ModsDir = 'D:\Minecraft\SKLauncher\sklauncher-data-v4\instances\test-1\mods'
)

$ErrorActionPreference = 'Stop'
$name = 'capatest-1.67.13.jar'
# Pinned to the JAR from the successful Forge run 44655102247.
$expected = '9d50d50d13da11048c964f5f7fbc4ec1686e8da88f60808fbda4a3ea5e07c249'
$source = Get-Item -LiteralPath $Jar
$mods = Get-Item -LiteralPath $ModsDir
if ($source -isnot [System.IO.FileInfo]) { throw 'Indica el archivo JAR extraido del ZIP.' }
if ($mods -isnot [System.IO.DirectoryInfo] -or $mods.Name -ne 'mods' -or
        ($mods.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Indica una carpeta mods existente, no un enlace o una union de directorios.'
}
if ((Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash -ne $expected) {
    throw 'SHA-256 distinto del JAR verificado. No se cambio ningun mod.'
}

$target = Join-Path $mods.FullName $name
$installed = @(Get-ChildItem -LiteralPath $mods.FullName -File -Force |
    Where-Object { $_.Name -like 'capatest-*.jar' })
foreach ($old in $installed) {
    if ($old.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Revisa el enlace antes de seguir: $($old.FullName)"
    }
}
if ($installed.Count -eq 1 -and $installed[0].Name -eq $name -and
        (Get-FileHash -LiteralPath $installed[0].FullName -Algorithm SHA256).Hash -eq $expected) {
    Write-Host "$name ya esta instalado y verificado en $($mods.FullName)."
    return
}
if (-not $PSCmdlet.ShouldProcess($mods.FullName, "Instalar $name y respaldar los JAR anteriores de capatest")) { return }

$id = [guid]::NewGuid().ToString('N')
$stage = Join-Path $mods.FullName ('.capatest-' + $id + '.tmp')
$backupRoot = Join-Path $mods.Parent.FullName 'capatest-respaldos'
if (Test-Path -LiteralPath $backupRoot) {
    $backupFolder = Get-Item -LiteralPath $backupRoot -Force
    if ($backupFolder -isnot [IO.DirectoryInfo] -or ($backupFolder.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "No se puede respaldar de forma segura en $backupRoot."
    }
}
$backup = Join-Path $backupRoot ((Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + $id)
$moved = @()
try {
    [IO.File]::Copy($source.FullName, $stage, $false)
    if ((Get-FileHash -LiteralPath $stage -Algorithm SHA256).Hash -ne $expected) {
        throw 'La copia temporal no coincide. No se cambio ningun mod.'
    }
    if ($installed.Count -gt 0) { [void][IO.Directory]::CreateDirectory($backup) }
    foreach ($old in $installed) {
        [IO.File]::Move($old.FullName, (Join-Path $backup $old.Name))
        $moved += $old
    }
    # The temporary copy is on the same volume. Move without overwriting.
    [IO.File]::Move($stage, $target)
} catch {
    $failure = $_
    foreach ($old in $moved) {
        try {
            [IO.File]::Move((Join-Path $backup $old.Name), $old.FullName)
        } catch {
            Write-Warning "No se pudo restaurar $($old.Name). Sigue guardado en $backup."
        }
    }
    throw $failure
} finally {
    if ([IO.File]::Exists($stage)) {
        try { [IO.File]::Delete($stage) }
        catch { Write-Warning "Quedo una copia temporal sin extension .jar en $stage." }
    }
}
Write-Host "$name instalado y verificado en $($mods.FullName)."
if ($moved.Count -gt 0) { Write-Host "JAR anteriores guardados en $backup." }
