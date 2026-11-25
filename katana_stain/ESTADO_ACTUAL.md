# Katana de Stain — estado y traspaso

Este es el punto de entrada vigente. Las secciones antiguas de `INTEGRACION.md` y los informes de `referencias/` son histórico; no deben interpretarse como afirmaciones actuales. La katana es un mod independiente `stainkatana` para Minecraft Java 1.20.1 / Forge 47, no la capa `capatest`.

> **Rama de trabajo:** todo este avance (código, capturas, documentación y el JAR de prueba) vive en `arena/ce4979c1-modelos`. El enlace de galería de la rama `arena/a09d390b-modelos` seguirá mostrando las imágenes antiguas hasta que este trabajo se fusione allí.

## Entrega e instalación

- `descargas/stainkatana-0.22.0-test.jar` es una **prueba experimental**, no una versión final. SHA-256: `b56e0f0ca20dad7e0db8b1cd329338e29012b23b63765a249e3c4b345401cbc3`. Lo compiló y verificó el workflow `45544953232` (compilación `45544081949`, ambos exitosos) y se re-verificó el hash contra el JAR publicado. El servidor Forge de prueba arrancó. Se compiló sobre el código del árbol actual (revert del pitch zurdo incluido). **No hay confirmación de que el usuario lo haya instalado ni probado.** La 0.20.0-test fue rechazada; la 0.21.0-test no consta como instalada ni aprobada y no se debe asumir nada sobre ella.
- `instalar-0.22-test.ps1` instala en `D:\Minecraft\SKLauncher\sklauncher-data-v4\instances\test-1\mods`; verifica el hash, sustituye solo la `0.20.0-test` rechazada y, si hay otras versiones de stainkatana (por ejemplo la 0.21.0-test), se detiene y pide retirarlas a mano. No hace respaldos. El JAR se descarga de la rama de trabajo (`arena/ce4979c1-modelos`); tras una fusión a `arena/a09d390b-modelos` debe actualizarse la URL del script.
- Requiere Forge 1.20.1, GeckoLib Forge 4.8.1 o compatible y PlayerAnimator Forge 1.0.2-rc1+1.20 o compatible. Better Combat es opcional, pero si está presente controla el combate ordinario; animaciones adaptadas proceden de **otros mods**, no de clips predeterminados de Better Combat ni de efectos de Darkest Hours. Las licencias y atribuciones de recursos incorporados están en `forge/resources/META-INF/` (añadida
  `KELVIN_BETTER_PLAYER_ANIMATIONS_LICENSE.txt`).
- **El código de la rama es posterior al JAR 0.21** y es el del JAR 0.22.0-test.

### Qué cambia en 0.22.0-test respecto a 0.21.0-test

- Corrección de un error de límites en `KatanaAnimations`: la tabla de clips tenía 16 entradas (ids 0–15) y el décimo golpe de C (id 16) no reproducía ninguna animación en clientes. Ahora el límite es `MAX_ANIMATION_ID = 16`.
- Variedad real para los cortes laterales de C: rotación determinista `stain_c_grip_trial` (Serious `sword_attack2`, MIT) → `stain_c_grip_trial2` (Serious `sword_attack`, ventanas de compensación escaladas a 0.875 s, `tools/adaptar_agarre_c.py`) → `kelvin_swing_first` / `kelvin_swing_second` (Kelvin's Better Player Animations, MIT, mod antiguo inactivo, `tools/adaptar_kelvin.py`). Los cortes 2, 5 y 8 de C conservan `stain_c_overhead`; la apertura sigue en `stain_c_overhead`.
- Clips nuevos validados por el verificador de PlayerAnimator (`verifyKatanaAnimations`, verde) y renderizados por tres clientes Forge reales (con BC, sin BC, con clips BC como recurso).
- En primera persona, la mano libre configurable (`blood_gesture.*`) se aplica a la mano **no principal** (zurdos incluidos), no siempre al brazo izquierdo.
- Se probó y **se revirtió** el pitch espejo (+45°) para la hoja zurda en tercera persona: en la vista trasera la hoja cruzaba la espalda. El encuadre zurdo sigue pendiente de diseño propio, no de ajustes ciegos.
- `mods.toml`, `build.gradle` y `.github/workflows/build.yml` quedaron en `0.22.0-test`; el job del JAR ahora reaplica su commit con rebase para no pisar pushes concurrentes del fixture.

## Estado funcional y visual

- Guardia solicitada: katana al costado, levantada y separada de la pierna. En las capturas actuales el encuadre diestro (04, 03) y zurdo desde atrás se ven razonables; la vista frontal zurda (00c) mejora frente a antes pero **no está aprobada**; falta un encuadre propio para zurdos. Mantener HUD, combate, audio y compatibilidad con Better Combat.
- Z: marcar un objetivo y paralizar/rematar según el estado. En primera persona zurda los brazos todavía parecen flotantes o solapados; la mano libre configurable ya se aplica a la mano no principal. El gesto completo, agarre y cámara necesitan revisión en movimiento.
- X: los encuadres de primera persona derecho y zurdo se bajaron; revisar continuidad, tamaño de brazos y visibilidad de la espada. El servidor comprueba obstrucción para evitar impactos detrás de paredes.
- C: el servidor programa diez golpes; las inmunidades, armadura y absorción pueden alterar resultados. La compensación de agarre por fases sigue siendo `stain_c_grip_trial`; se añadió `stain_c_grip_trial2` y dos clips de Kelvin con la misma compensación. Las fases 114–118 (diestra) y 119–123 (zurda) siguen siendo muestras sin víctima; las nuevas 124–127 (trial2), 128–131 (kelvin1), 132–135 (kelvin2) y 136–139 (kelvin1 zurda) muestran: anticipación con dos manos conectadas (kelvin 129/133), contactos con la hoja a la cintura o invisible de frente, y recuperaciones bajas. Ninguna fase ni sincronía está aprobada; la captura ocurre después del evento de daño, no en el fotograma de contacto.
- Los impactos confirmados del servidor (01–10) siguen siendo capturas posteriores al daño; bajo latencia real el desajuste puede ser mayor.
- Better Combat controla el combate ordinario si está instalado; sus clips predeterminados no se usan para las habilidades. El audio de las habilidades usa `bettercombat:katana_slash` si existe, con alternativa vanilla; **el audio no se ha escuchado ni aprobado**.

## Validación reproducible y capturas

`python3 katana_stain/tools/preparar_test.py`, `verificar_test.py` y `verificar_modelo.py` hacen comprobaciones locales. Los tests de Java/Forge se ejecutan en GitHub Actions. El workflow `.github/workflows/katana-visual.yml` lanza tres clientes Forge reales bajo Xvfb. En esta iteración el workflow visual `45543014805` y las compilaciones `45544081949` y `45544953232` quedaron en verde (incluye arranque de servidor dedicado, verificación de assets, los diez impactos confirmados de C y el test de encuadre de brazos). Aun así, una imagen posterior al evento de daño no equivale al fotograma exacto de contacto; la aprobación visual y la escucha del audio siguen pendientes.

- [Galería y tiempos](vistas/GALERIA.md); imágenes en `vistas/client-full-bc`, `client-vanilla` y `client-test`. Enlaces bajo la rama `arena/ce4979c1-modelos`. El bot actualiza las carpetas y puede avanzar la rama: hacer fetch y fast-forward antes de nuevos cambios.
- El filtro de visibilidad de brazos `tools/verificar_encuadre_fixture.py` detecta brazos totalmente fuera de cuadro en su fixture controlado; **no** prueba que el agarre ni la postura sean correctos.

## Próximos pasos

1. Inspeccionar en juego (playtest humano) Z/X/C en primera y tercera persona, ambas manos, frente a objetivo y con ángulos laterales; el fixture solo muestrea frente. Confirmar si la rotación Kelvin mejora o empeora el contacto percibido.
2. Revisar o rediseñar los brazos de Z zurdo y la primera persona de X sin romper los hombros ni el agarre; conservar la guardia al costado. Probar con obstáculos y enemigos grandes.
3. Validar agarre, variedad y sincronización de C bajo latencia real; considerar capturas laterales del fixture (o escenas de C completas) si las muestras frontales no bastan. No entregar el JAR como definitivo por una CI verde.
4. Escuchar el audio en juego (Z/X/C, con y sin Better Combat) y ajustar; nadie lo ha aprobado todavía.
5. Si se genera otra versión del JAR, incrementar el número (0.23.0-test o posterior), comprobar su SHA-256 contra lo publicado y actualizar `instalar-*.ps1`. No afirmar aprobación visual solo por pruebas automáticas.

## Archivos clave y precauciones

`forge/java/com/stainkatana/katana/KatanaAbilities.java`, `CombatTuning.java`, `AbilityTimeline.java`, `KatanaRenderer.java`, `client/KatanaAnimations.java`, `client/KatanaScene.java`; `forge/resources/assets/stainkatana/player_animation/` (incluye `stain_c_grip_trial.json`, `stain_c_grip_trial2.json`, `kelvin_swing_first.json`, `kelvin_swing_second.json`); `forge/resources/META-INF/KELVIN_BETTER_PLAYER_ANIMATIONS_LICENSE.txt`; `tools/adaptar_agarre_c.py`, `tools/adaptar_kelvin.py`; `visual_test/`; `.github/workflows/katana-visual.yml`, `.github/workflows/build.yml`. Conservar `.katana_lab/` y los PNG no rastreados existentes. El usuario autorizó sincronizar conflictos locales con la rama remota, pero no crear respaldos. No alterar la capa `capatest` sin motivo.
