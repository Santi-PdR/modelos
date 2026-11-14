#!/usr/bin/env python3
"""Restaura el icono APROBADO (v1.13) desde su backup byte-idéntico.

Uso:  python3 tools/restore_icon.py
Tras ejecutarlo, comenta la llamada a build_icon() en main() de
texture_pipeline.py (o vuelve a registrar el generador anterior) si quieres
que un rebuild no lo vuelva a remasterizar.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "tools" / "originals" / "icono_aprobado_v1130.png"
DEST = ROOT / "src/main/resources/assets/capatest/textures/item/capa_deteriorer_evilsaiyan.png"
assert BACKUP.is_file(), "falta el backup del icono aprobado"
shutil.copy(BACKUP, DEST)
print("icono aprobado restaurado en", DEST.relative_to(ROOT))
