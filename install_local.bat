@echo off
REM ============================================================
REM  install_local.bat  - Instala el JAR y el .bbmodel localmente
REM
REM  1. Copia el JAR del mod en:
REM       D:\Minecraft\SKLauncher\sklauncher-data-v4\instances\test-1\mods
REM      Borrando ANTIGUAS versiones del jar (capatest-*.jar) antes.
REM  2. Copia el .bbmodel en:
REM       C:\Users\santi\Downloads
REM
REM  Uso:
REM    install_local.bat [ruta\del\capatest-1.29.0.jar] [ruta\del\CAPA_v1.29.0.bbmodel]
REM
REM  Si no se pasan argumentos, busca los archivos en:
REM    entregables\capatest-1.29.0.jar
REM    docs\CAPA_v1.29.0.bbmodel
REM  (relativos a la carpeta donde se ejecute el script).
REM ============================================================
setlocal enableextensions

REM --- Rutas de destino ---
set "MODS_DIR=D:\Minecraft\SKLauncher\sklauncher-data-v4\instances\test-1\mods"
set "DOWNLOADS_DIR=C:\Users\santi\Downloads"

REM --- Archivos de origen (argumentos o por defecto) ---
set "JAR_SRC=%~1"
set "BB_SRC=%~2"
if "%JAR_SRC%"=="" set "JAR_SRC=entregables\capatest-1.29.0.jar"
if "%BB_SRC%"==""  set "BB_SRC=docs\CAPA_v1.29.0.bbmodel"

echo.
echo ============================================================
echo  Instalacion local del mod Capa Deteriorer Test
echo ============================================================
echo  JAR origen    : %JAR_SRC%
echo  BBModel origen: %BB_SRC%
echo  MODS destino  : %MODS_DIR%
echo  DOWNLOADS      : %DOWNLOADS_DIR%
echo.

REM --- Comprobar que los archivos de origen existen ---
if not exist "%JAR_SRC%" (
    echo  [FALLO] No existe el JAR: %JAR_SRC%
    echo  Pon la ruta del .jar como primer argumento.
    exit /b 1
)
if not exist "%BB_SRC%" (
    echo  [FALLO] No existe el .bbmodel: %BB_SRC%
    echo  Pon la ruta del .bbmodel como segundo argumento.
    exit /b 1
)

REM --- Nombres de archivo desde la ruta de origen ---
for %%F in ("%JAR_SRC%") do set "JAR_FILE=%%~nxF"
for %%F in ("%BB_SRC%") do set "BB_FILE=%%~nxF"

REM --- Crear los directorios de destino si no existen ---
if not exist "%MODS_DIR%" (
    echo  [WARN] El directorio de mods no existe: %MODS_DIR%
    echo  Creandolo...
    mkdir "%MODS_DIR%" 2>nul
    if not exist "%MODS_DIR%" (
        echo  [FALLO] No se pudo crear %MODS_DIR%. Revisa la ruta.
        exit /b 1
    )
)
if not exist "%DOWNLOADS_DIR%" (
    echo  [WARN] No existe %DOWNLOADS_DIR%, creandolo...
    mkdir "%DOWNLOADS_DIR%" 2>nul
)

REM --- 1) MODS: borrar versiones VIEJAS del jar e instalar el nuevo ---
echo.
echo [1] Limpiando versiones antiguas del jar en: %MODS_DIR%
if exist "%MODS_DIR%\capatest-*.jar" (
    del /q "%MODS_DIR%\capatest-*.jar" >nul 2>&1
    echo    Borradas las versiones anteriores de capatest-*.jar
) else (
    echo    No habia jar antiguo que borrar
)

copy /y "%JAR_SRC%" "%MODS_DIR%\%JAR_FILE%" >nul
if errorlevel 1 (
    echo  [FALLO] No se pudo copiar el JAR a %MODS_DIR%
    exit /b 1
)
echo    Jar instalado: %MODS_DIR%\%JAR_FILE%

REM --- 2) BBMODEL en Downloads ---
echo.
echo [2] Copiando el .bbmodel a: %DOWNLOADS_DIR%
copy /y "%BB_SRC%" "%DOWNLOADS_DIR%\%BB_FILE%" >nul
if errorlevel 1 (
    echo  [FALLO] No se pudo copiar el .bbmodel a %DOWNLOADS_DIR%
    exit /b 1
)
echo    Bbmodel instalado: %DOWNLOADS_DIR%\%BB_FILE%

echo.
echo ============================================================
echo  Instalacion OK
echo  - JAR    : %MODS_DIR%\%JAR_FILE%
echo  - BBMODEL: %DOWNLOADS_DIR%\%BB_FILE%
echo ============================================================
echo.
endlocal
exit /b 0
