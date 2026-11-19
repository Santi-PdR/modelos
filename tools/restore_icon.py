#!/usr/bin/env python3
"""Exporta el icono aprobado de v1.13 sin tocar el atlas animado activo."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / 'tools/originals/icono_aprobado_v1130.png'
DEST = ROOT / 'entregables/icono_aprobado_v1130.png'
DEST.parent.mkdir(exist_ok=True)
shutil.copyfile(BACKUP, DEST)
print('Icono histórico exportado en', DEST.relative_to(ROOT))
