# Backup del icono aprobado (v1.13 / Blight Star)

`ICONO_APROBADO_BACKUP.png` es una copia **byte-idéntica** del icono de 64×64
que el usuario aprobó y que estuvo activo hasta v1.17.0 v1220.

- SHA-256: `e88ccec0a0c67b1ad0982ed781f0d684ae4662660c545fa134574781967e4840`
- Copia de seguridad adicional para CI: `tools/originals/icono_aprobado_v1130.png`
- Técnica: pixel art 16×16 ampliado 4× con NEAREST, paleta plana, sin AA/bloom.

Si la remasterización no convence, basta con copiar cualquiera de estas dos
imágenes sobre `src/main/resources/assets/capatest/textures/item/capa_deteriorer_evilsaiyan.png`
o, más sencillo, ejecutar `python3 tools/restore_icon.py`. Ten en cuenta que
`tools/texture_pipeline.py` REGENERA el icono en cada ejecución: para que la
restauración sea permanente hay que desactivar `build_icon()` en `main()`.

`tools/audit_model.py` verifica en cada CI que este backup sigue intacto.
