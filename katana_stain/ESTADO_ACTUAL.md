# Katana de Stain — estado y traspaso

Este es el punto de entrada vigente. Las secciones antiguas de `INTEGRACION.md` y los informes de `referencias/` son histórico; no deben interpretarse como afirmaciones actuales. La katana es un mod independiente `stainkatana` para Minecraft Java 1.20.1 / Forge 47, no la capa `capatest`.

## Entrega e instalación

- `descargas/stainkatana-0.21.0-test.jar` es una **prueba experimental**, no una versión final. SHA-256: `c84724ae1c6f5c8fe7abb74b36a5b0b55e3d2a1054c1dc6661ef07aebea1d857`. Se compiló y verificó en el workflow `45501118241`; el servidor Forge de prueba arrancó. Se ofreció al usuario, pero **no hay confirmación de que haya instalado o probado con éxito**.
- `instalar-0.21-test.ps1` instala en `D:\Minecraft\SKLauncher\sklauncher-data-v4\instances\test-1\mods`; verifica el hash y solo sustituye la `0.20.0-test` concreta después de descargar y comprobar el nuevo archivo. Se detiene si hay otras versiones de stainkatana o el antiguo `capatest-0.1.0-katana-test.jar`. El primer script tenía un carácter extra en el hash; fue corregido en `54420e9` y el valor actual se verificó contra el JAR. No hacer respaldos.
- Requiere Forge 1.20.1, GeckoLib Forge 4.8.1 o compatible y PlayerAnimator Forge 1.0.2-rc1+1.20 o compatible. Better Combat es opcional, pero si está presente controla el combate ordinario; animaciones adaptadas proceden de **otros mods**, no de clips predeterminados de Better Combat. No usar efectos de Darkest Hours. Las licencias y atribuciones de recursos incorporados están en `forge/resources/META-INF/`.
- **El código de la rama es posterior al JAR 0.21**. El ensayo de agarre de C descrito abajo no está incluido en ese JAR. No confundir JAR con fuente actual ni reutilizar 0.20, que el usuario rechazó.

## Estado funcional y visual

- Guardia solicitada: katana al costado, levantada y separada de la pierna. La guardia reciente mejoró en capturas, pero el usuario no la ha aprobado. Mantener HUD, combate, audio y compatibilidad con Better Combat.
- Z: marcar un objetivo y paralizar/rematar según el estado. En primera persona zurda los brazos todavía parecen flotantes o solapados. El gesto completo, agarre y cámara necesitan revisión en movimiento.
- X: los encuadres de primera persona derecho y zurdo se bajaron; revisar continuidad, tamaño de brazos y visibilidad de la espada. El servidor comprueba obstrucción para evitar impactos detrás de paredes.
- C: el servidor programa diez golpes. La prueba con objetivo débil y resistente comprobó diez eventos de daño y descensos de salud; inmunidades, armadura, absorción y otros mods pueden alterar resultados. El ensayo reciente `stain_c_grip_trial` deriva del clip de Serious Player Animations y corrige la posición del ítem por fases. En capturas aisladas mejora el agarre en parte del corte, pero no demuestra agarre perfecto, continuidad o contacto con el objetivo: la coreografía, efectos y cámara aún no están aprobados. Su generador es `tools/adaptar_agarre_c.py`. No convertir esta prueba en release por una CI verde.
- Se probaron cuatro animaciones externas distintas de Better Combat en golpes reales a un objetivo, con daño comprobado en el servidor. Eso no sustituye la revisión visual ni el playtest humano. El audio no se ha escuchado ni aprobado aquí.

## Validación reproducible y capturas

`python3 katana_stain/tools/preparar_test.py`, `verificar_test.py` y `verificar_modelo.py` hacen comprobaciones locales. Los tests de Java/Forge se ejecutan en GitHub Actions. El workflow `.github/workflows/katana-visual.yml` lanza tres clientes Forge reales bajo Xvfb: recursos BC, vanilla y Better Combat completo. También comprueba ataques, daño, cancelación, cámara y visibilidad de brazos en una escena/skin fijas. Una imagen posterior al evento de daño no equivale al fotograma exacto de contacto.

- Último ensayo del agarre por fases: visual `45539185719` y compilación `45539185668`, ambos `success`. Contiene capturas locales 114–118 diestras y 119–123 zurdas; la muestra no tiene objetivo y no valida sincronización del servidor. El fixture también capturó impactos confirmados.
- [Galería y tiempos](vistas/GALERIA.md); imágenes en `vistas/client-full-bc`, `client-vanilla` y `client-test`. El bot actualiza las carpetas y puede avanzar la rama: hacer fetch y fast-forward antes de nuevos cambios.
- El filtro de visibilidad de brazos `tools/verificar_encuadre_fixture.py` detecta brazos totalmente fuera de cuadro en su fixture controlado; **no** prueba que el agarre ni la postura sean correctos.

## Próximos pasos

1. Inspeccionar el ensayo de C en las cinco fases de ambas manos y con objetivo desde ángulos adicionales; comprobar que la compensación no produzca desplazamientos bruscos ni separación en cuadros intermedios, y que el golpe visual coincida con daño bajo latencia.
2. Revisar o rediseñar los brazos de Z zurdo y la primera persona de X sin romper los hombros ni el agarre; conservar la guardia al costado. Probar tercera persona, primera persona, diestros/zurdos y obstáculos.
3. Mejorar variedad de C sin usar animaciones predeterminadas de Better Combat; el código debe seguir respetando el calendario de golpes del servidor. Consultar los experimentos fallidos de `referencias/cinematica_combate_analisis.md` antes de repetir ajustes.
4. Probar modpack, audio y movimiento con el usuario. Cuando corresponda generar un JAR de **versión nueva**, probar su contenido reobfuscado y hash, y pasar PowerShell para la carpeta indicada. No afirmar aprobación visual solo por pruebas automáticas.

## Archivos clave y precauciones

`forge/java/com/stainkatana/katana/KatanaAbilities.java`, `CombatTuning.java`, `AbilityTimeline.java`, `KatanaRenderer.java`, `client/KatanaAnimations.java`, `client/KatanaScene.java`; `forge/resources/assets/stainkatana/player_animation/`; `visual_test/`; `.github/workflows/katana-visual.yml`. Conservar `.katana_lab/` y los PNG no rastreados existentes. El usuario autorizó sincronizar conflictos locales con la rama remota, pero no crear respaldos. No alterar la capa `capatest` sin motivo.
