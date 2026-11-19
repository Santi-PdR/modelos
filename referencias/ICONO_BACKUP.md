# Backups de iconos

Los iconos históricos se conservan byte a byte y se verifican por SHA-256
en `tools/audit_model.py`. No son el recurso activo de la hotbar.

| Fichero | SHA-256 | Qué es |
|---|---|---|
| `ICONO_APROBADO_BACKUP.png` | `e88ccec0…e4840` | Icono **APROBADO** de 64×64 (pixel art 16×16 ampliado 4× con NEAREST, paleta plana, sin AA/bloom), activo hasta v1.17.0 v1220. Tesis Blight Star. |
| `ICONO_V125_PREFERIDO_BACKUP.png` | `c90670ba…0ee5` | Icono **PREFERIDO** de la v1.25.0: el que el usuario pidió recuperar ("el 1 era mucho mejor"). A partir de la v1.27.0 el icono activo es otro, así que esta copia conserva el preferido byte a byte. |
| `ICONO_PREFERIDO_BACKUP.png` | `c90670ba…0ee5` | Otra copia histórica del PREFERIDO de v1.25.0. |
| `ICONO_V1270_REDISEÑO_BACKUP.png` | `1500c073…952c` | Rediseño temporal de v1.27.0. |

Copias de seguridad adicionales para CI:

- `tools/originals/icono_aprobado_v1130.png` (idéntico al aprobado).
- `docs/ICONO_APROBADO_BACKUP.png` (idéntico al aprobado; copia de muestra).

## Exportar un icono histórico

`python3 tools/restore_icon.py` copia el icono **APROBADO** de la v1.13 a
`entregables/icono_aprobado_v1130.png`. No sobrescribe la tira animada: un
PNG estático por sí solo no coincide con su `.png.mcmeta`.

**No confundir**: `ICONO_V125_PREFERIDO_BACKUP.png` es el PREFERIDO;
`ICONO_APROBADO_BACKUP.png` es el APROBADO de la v1.13. Son iconos distintos
y tienen SHA distintos.

## v1.67.6 — referencia elegida

El icono activo procede de `REFERENCIA_ICONO_v1676.png`. El sprite anterior
se conserva en `docs/respaldos/v1.65.0/textures/item/`; los PNG de este
directorio siguen siendo copias históricas, no recursos del atlas animado.

## v1.67.7 — referencia de jirones rosas

`REFERENCIA_ICONO_v1677.png` es el nuevo dibujo tal cual se recibió.
`tools/cape_icon.py` quita el damero, encuadra el sprite con más presencia y
anima sus grietas. `ICONO_V1676_BACKUP.png` conserva el fotograma en reposo
de la versión anterior; la tira completa está en el tag `v1.67.6`.

## v1.67.8 — mismo dibujo, pulso más fluido

`ICONO_V1677_PULSO.png` conserva la tira anterior completa (64×1024,
16 cuadros, 2 ticks por cuadro). Su primer fotograma es idéntico al del
icono actual. La tira activa tiene 32 cuadros a 1 tick y el mismo ciclo.
