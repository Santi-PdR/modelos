# Katana 0.27.0-test: version experimental, no definitiva.
# Cierra Minecraft y SKLauncher antes de ejecutar.
# Instala SOLO en la instancia test-1 de SKLauncher; no toca ninguna otra.
$ErrorActionPreference = 'Stop'
$mods = 'D:\Minecraft\SKLauncher\sklauncher-data-v4\instances\test-1\mods'
$name = 'stainkatana-0.27.0-test.jar'
# SHA-256 del archivo publicado por esta rama (verificado contra el JAR publicado):
$sha = 'EFDE57416F5A20E4A9BBCF6B7D3AD6202C29F899ED85DE5FF6BD9108AC9FDBB1'
$url = 'https://github.com/Santi-PdR/modelos/raw/refs/heads/arena/ce4979c1-modelos/katana_stain/descargas/stainkatana-0.27.0-test.jar'
# La 0.20.0-test fue rechazada; la 0.21.0-test, la 0.22.0-test y la 0.23.0-test, la 0.24.0-test, la 0.25.0-test y la 0.26.0-test
# no constan como instaladas ni aprobadas: todas se retiran solas. Cualquier
# OTRA versión stainkatana-*.jar (desconocida) detiene la instalación.
if (-not (Test-Path -LiteralPath $mods -PathType Container)) { throw "No existe la carpeta de mods: $mods" }
if (Get-Process -Name 'javaw','java' -ErrorAction SilentlyContinue) { throw 'Cierra Minecraft y cualquier proceso Java antes de instalar.' }
$retirable = 'stainkatana-0.20.0-test.jar'
$retirable21 = 'stainkatana-0.21.0-test.jar'
$retirable22 = 'stainkatana-0.22.0-test.jar'
$retirable23 = 'stainkatana-0.23.0-test.jar'
$retirable24 = 'stainkatana-0.24.0-test.jar'
$retirable25 = 'stainkatana-0.25.0-test.jar'
$retirable26 = 'stainkatana-0.26.0-test.jar'
$other = @(Get-ChildItem -LiteralPath $mods -Filter 'stainkatana-*.jar' -File | Where-Object { $_.Name -ne $name -and $_.Name -ne $retirable -and $_.Name -ne $retirable21 -and $_.Name -ne $retirable22 -and $_.Name -ne $retirable23 -and $_.Name -ne $retirable24 -and $_.Name -ne $retirable25 -and $_.Name -ne $retirable26 })
if (Test-Path -LiteralPath (Join-Path $mods 'capatest-0.1.0-katana-test.jar')) { throw 'Retira manualmente capatest-0.1.0-katana-test.jar: entra en conflicto con la capa.' }
if ($other.Count -gt 0) { throw ('Retira manualmente las otras versiones de stainkatana antes de instalar (versión desconocida): ' + (($other | ForEach-Object Name) -join ', ')) }
if (-not (Get-ChildItem -LiteralPath $mods -Filter '*geckolib*.jar' -File)) { Write-Warning 'Falta GeckoLib Forge 4.8.1 o compatible.' }
if (-not (Get-ChildItem -LiteralPath $mods -Filter '*player*anim*.jar' -File)) { Write-Warning 'Falta PlayerAnimator Forge 1.0.2-rc1+1.20 o compatible.' }
$tmp = Join-Path $mods ($name + '.download')
try {
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $tmp
    if ((Get-FileHash -LiteralPath $tmp -Algorithm SHA256).Hash -ne $sha) { throw 'SHA-256 incorrecto: no se instala el archivo.' }
    Move-Item -LiteralPath $tmp -Destination (Join-Path $mods $name) -Force
    foreach ($retirableN in $retirable, $retirable21, $retirable22, $retirable23, $retirable24, $retirable25, $retirable26) {
        $old = Join-Path $mods $retirableN
        if (Test-Path -LiteralPath $old -PathType Leaf) { Remove-Item -LiteralPath $old -Force }
    }
    Write-Host "Instalada la version experimental en $mods"
    Write-Warning 'Z zurdo sigue sin resolver brazos flotantes/solapados. El agarre, la variedad y la sincronizacion de C NO estan aprobados. Esto no es la version final.'
} finally {
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force }
}
