# Katana 0.21.0-test: version experimental, no definitiva.
# Cierra Minecraft y SKLauncher antes de ejecutar.
$ErrorActionPreference = 'Stop'
$mods = 'D:\Minecraft\SKLauncher\sklauncher-data-v4\instances\test-1\mods'
$name = 'stainkatana-0.21.0-test.jar'
$sha = 'C84724AE1C6F5C8FE7ABB74B36A5B0B55E3D2A1054C1DC6661EFE07AEBEA1D857'
$url = 'https://github.com/Santi-PdR/modelos/raw/refs/heads/arena/a09d390b-modelos/katana_stain/descargas/stainkatana-0.21.0-test.jar'
if (-not (Test-Path -LiteralPath $mods -PathType Container)) { throw "No existe la carpeta de mods: $mods" }
if (Get-Process -Name 'javaw','java' -ErrorAction SilentlyContinue) { throw 'Cierra Minecraft y cualquier proceso Java antes de instalar.' }
$other = @(Get-ChildItem -LiteralPath $mods -Filter 'stainkatana-*.jar' -File | Where-Object { $_.Name -ne $name -and $_.Name -ne 'stainkatana-0.20.0-test.jar' })
if (Test-Path -LiteralPath (Join-Path $mods 'capatest-0.1.0-katana-test.jar')) { throw 'Retira manualmente capatest-0.1.0-katana-test.jar: entra en conflicto con la capa.' }
if ($other.Count -gt 0) { throw ('Retira manualmente las otras versiones de stainkatana antes de instalar: ' + (($other | ForEach-Object Name) -join ', ')) }
if (-not (Get-ChildItem -LiteralPath $mods -Filter '*geckolib*.jar' -File)) { Write-Warning 'Falta GeckoLib Forge 4.8.1 o compatible.' }
if (-not (Get-ChildItem -LiteralPath $mods -Filter '*player*anim*.jar' -File)) { Write-Warning 'Falta PlayerAnimator Forge 1.0.2-rc1+1.20 o compatible.' }
$tmp = Join-Path $mods ($name + '.download')
try {
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $tmp
    if ((Get-FileHash -LiteralPath $tmp -Algorithm SHA256).Hash -ne $sha) { throw 'SHA-256 incorrecto: no se instala el archivo.' }
    Move-Item -LiteralPath $tmp -Destination (Join-Path $mods $name) -Force
    $old = Join-Path $mods 'stainkatana-0.20.0-test.jar'
    if (Test-Path -LiteralPath $old -PathType Leaf) { Remove-Item -LiteralPath $old -Force }
    Write-Host "Instalada la version experimental en $mods"
    Write-Warning 'Z zurdo y el agarre en C siguen teniendo fallos visuales. Esto no es la version final.'
} finally {
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force }
}
