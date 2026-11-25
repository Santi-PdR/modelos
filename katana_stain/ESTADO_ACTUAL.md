# Katana de Stain — estado y traspaso

Este es el punto de entrada vigente. Las secciones antiguas de `INTEGRACION.md` y los informes de `referencias/` son histórico; no deben interpretarse como afirmaciones actuales. La katana es un mod independiente `stainkatana` para Minecraft Java 1.20.1 / Forge 47, no la capa `capatest`.

> **Rama de trabajo:** todo este avance (código, capturas, documentación y el JAR de prueba) vive en `arena/ce4979c1-modelos`. El enlace de galería de la rama `arena/a09d390b-modelos` seguirá mostrando las imágenes antiguas hasta que este trabajo se fusione allí.

## Entrega e instalación

- El JAR publicado en `descargas/` sigue siendo `stainkatana-0.22.0-test.jar` (SHA-256 `b56e0f0ca20dad7e0db8b1cd329338e29012b23b63765a249e3c4b345401cbc3`, compilado por el workflow `45544953232`). **No está confirmado que el usuario lo haya instalado ni probado.** La 0.20.0-test fue rechazada; la 0.21.0-test no consta como instalada ni aprobada.
- El árbol de la rama ya es **0.23.0-test** (`build.gradle`, `mods.toml` y workflow). Cuando el workflow de esta iteración almacene el JAR 0.23.0-test en `descargas/`, este archivo se actualizará con su SHA-256 y `instalar-0.23-test.ps1` será el instalador vigente.
- `instalar-0.22-test.ps1` instala en `D:\Minecraft\SKLauncher\sklauncher-data-v4\instances\test-1\mods`; valida el hash, sustituye solo la 0.20.0-test rechazada y **se detiene** si hay otras versiones. Cuando exista 0.23.0-test se publicará `instalar-0.23-test.ps1` con la misma disciplina; el instalador nuevo debe sustituir también la 0.22 si estuviera instalada. Sin respaldos.
- Requiere Forge 1.20.1, GeckoLib Forge 4.8.1 o compatible y PlayerAnimator Forge 1.0.2-rc1+1.20 o compatible. Better Combat es opcional y controla el combate ordinario; las animaciones proceden de **otros mods**. Las atribuciones están en `forge/resources/META-INF/` (Se añaden desde siempre: Cinema Scope, Kelvin (ahora con variantes `_sneak`), Serious Player Animations, Better Combat Particle, Emotecraft, etc.).
- Investigación de mods para cinemática y FX: `referencias/cinematicas_fx_analisis.md` (Oborokage MIT — técnicas adaptadas como código propio; SlashBlade y TheDarkDimensions sin licencia — no usables; Epic Fight — conceptos).

### Qué cambia en 0.23.0-test respecto a 0.22.0-test

- **Más variedad real en C**: dos cortes nuevos adaptados de Kelvin's Better Player Animations (MIT): `kelvin_swing_first_sneak` y `kelvin_swing_second_sneak` (misma estocada, postura agazapada más profunda), reescalados a 0.9 s con la misma compensación `rightItem`. La rotación lateral de C pasa de 4 a **6** cortes (serias → kelvin → kelvin agazapados). El mapeo de IDs de animación y el protocolo visual v11 no cambian.
- **Impacto decisivo con más cuerpo**:
  - sacudida de cámara view-only por golpe (`applyShake`, 0.45× en cortes normales, 1.0× en la ejecución decisiva, decae en 7 ticks, configurable `screenShakeDegrees` 0–4; default 1.1);
  - rim flash carmesí de 6 ticks en `ULTIMATE_FINAL` (C) y `FINISHER` (Z) (`finalFlash`);
  - tarjeta de título "S E N T E N C E" / "P A R A L Y S I S" con subtítulo "v e r e d i c t o final" (`titleCard`);
  - impulso de FOV por impacto decisivo ×1.8;
  - partícula propia nueva `blood_mote` (6 frames reutilizados de `blood_pulse`, tinte #FFF3D6), poblada en la ejecución decisiva; el build aislado sigue sin usar `ParticleTypes.` de vanilla.
- Todo lo anterior en `KatanaClientConfig` (`screenShakeDegrees`, `finalFlash`, `titleCard`), desactivable por el jugador. La **severidad visual** y el **agarre** siguen sin aprobarse: las capturas 124–139 siguen valiendo como muestras (los 6 nuevos cortes conservan las posiciones 0–3, así que las muestras previas siguen representando los mismos clips; los dos agazapados ocupan los slots 4–5).
- El revert de la hipótesis de guardia zurda (+45°) sigue vigente; el encuadre zurdo sigue siendo trabajo de diseño, no de ajustes ciegos. El décimo golpe de C reproduce clip desde 0.22.0-test.

## Estado funcional y visual

- Guardia diestra razonable en capturas; zurda no aprobada (frontal mejorada, sin resolver). Z zurdo de primera persona sigue con brazos flotantes/solapados; X revisado pero sin continuidad comprobada en juego.
- C: servidor programa diez golpes con teleport e inmunidades/armadura/absorción; el cliente ve la rotación de 6 cortes. **Nada de esto está validado en juego humano.** Los impactos confirmados se capturan después del evento de daño; la sincronización bajo latencia real es desconocida.
- Cámara, partículas, letra y sacudida son presentación local: nunca cambian objetivo, daño ni servidor.
- Better Combat controla el combate ordinario si está instalado; sus clips predeterminados no se usan; audio de habilidades vía `bettercombat:katana_slash` con alternativa vanilla; **el audio no se ha escuchado ni aprobado**.

## Validación reproducible y capturas

`python3 katana_stain/tools/preparar_test.py`, `verificar_test.py` (ampliado: cubre `blood_mote`, sacudida, flash y tarjeta de título y los 8 clips) y `verificar_modelo.py`. Los tests Java/Forge se ejecutan en GitHub Actions. El workflow visual (`[katana-visual]`) lanza tres clientes Forge bajo Xvfb. En 0.22.0-test, compilaciones y clientes quedaron en verde; para 0.23.0-test la validación equivalente es obligatoria antes de dar nada por probado.

- [Galería y tiempos](vistas/GALERIA.md); imágenes en `vistas/client-full-bc`, `client-vanilla` y `client-test`. Enlaces bajo la rama `arena/ce4979c1-modelos`.

## Próximos pasos

1. Playtest humano Z/X/C en primera/tercera persona, ambas manos, con objetivo y ángulos laterales; revisar la rotación de 6 cortes (¿los agazapados se leen como golpes bajos?), el shake, el rim flash y la tarjeta de título. Desactivarlos si molestan (config).
2. Rediseñar brazos zurdos de Z y primera persona de X sin romper hombros; conservar guardia al costado; probar obstáculos y enemigos grandes.
3. Iaido real: sistema de vaina en cintura/espalda (como `WaistSheaths` de Oborokage, MIT) + clip de desenvainado propio; es el salto visual pendiente más grande y no hay fuente con licencia compatible incorporable hoy.
4. Hit-stop en el remate decisivo (decidir si solo single-player o también red; el timing actual depende del servidor).
5. Escuchar el audio (Z/X/C, con y sin Better Combat) y ajustar; nunca aprobado.
6. Al generar otra versión del JAR, incrementar el número, comprobar SHA-256 contra lo publicado y actualizar `instalar-*.ps1`. No afirmar aprobación visual solo por CI.

## Archivos clave y precauciones

`forge/java/com/stainkatana/katana/KatanaAbilities.java`, `CombatTuning.java`, `AbilityTimeline.java`, `KatanaRenderer.java`, `client/KatanaAnimations.java`, `client/KatanaScene.java` (shake, rim flash, tarjeta), `client/KatanaVisuals.java`, `client/KatanaParticle(Registration).java`, `KatanaParticles.java` (MOTE), `KatanaClientConfig.java`; `forge/resources/assets/stainkatana/player_animation/`; `forge/resources/assets/stainkatana/particles/blood_mote.json`; `tools/adaptar_kelvin.py`; `.github/workflows/katana-visual.yml`, `.github/workflows/build.yml`; `referencias/cinematicas_fx_analisis.md`. Conservar `.katana_lab/` y los PNG no rastreados existentes. El usuario autorizó sincronizar conflictos locales con la rama remota, pero no crear respaldos. No alterar la capa `capatest` sin motivo. La `build-katana-input/` es local y re-generable (`preparar_test.py`); está en `.gitignore`.
