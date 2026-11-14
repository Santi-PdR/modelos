# Backups de iconos

Hay **tres** copias de iconos históricos en el repo. Ninguna se borra: cada
una es la referencia de un diseño distinto y todas están verificadas por
SHA-256 en `tools/audit_model.py`.

| Fichero | SHA-256 | Qué es |
|---|---|---|
| `ICONO_APROBADO_BACKUP.png` | `e88ccec0…e4840` | Icono **APROBADO** de 64×64 (pixel art 16×16 ampliado 4× con NEAREST, paleta plana, sin AA/bloom), activo hasta v1.17.0 v1220. Tesis Blight Star. |
| `ICONO_V125_PREFERIDO_BACKUP.png` | `c90670ba…0ee5` | Icono **PREFERIDO** de la v1.25.0: el que el usuario pidió recuperar ("el 1 era mucho mejor"). A partir de la v1.27.0 el icono activo es otro, así que esta copia conserva el preferido byte a byte. |
| `ICONO_PREFERIDO_BACKUP.png` | = SHA del icono **activo** | Copia byte-idéntica del icono que está en `src/main/resources/assets/capatest/textures/item/capa_deteriorer_evilsaiyan.png`. En la v1.27.0 es `1500c073…952c`. |

Copias de seguridad adicionales para CI:

- `tools/originals/icono_aprobado_v1130.png` (idéntico al aprobado).
- `docs/ICONO_APROBADO_BACKUP.png` (idéntico al aprobado; copia de muestra).

## Restaurar un icono

Si un rediseño no convence, basta con copiar cualquiera de estos PNG sobre
`src/main/resources/assets/capatest/textures/item/capa_deteriorer_evilsaiyan.png`
o, más sencillo, ejecutar `python3 tools/restore_icon.py` (que restaura el
icono **APROBADO** de la v1.13). Ten en cuenta que
`tools/texture_pipeline.py` REGENERA el icono en cada ejecución: para que la
restauración sea permanente hay que desactivar `build_icon()` en `main()`.

**No confundir**: `ICONO_V125_PREFERIDO_BACKUP.png` es el PREFERIDO;
`ICONO_APROBADO_BACKUP.png` es el APROBADO de la v1.13. Son iconos distintos
y tienen SHA distintos.
