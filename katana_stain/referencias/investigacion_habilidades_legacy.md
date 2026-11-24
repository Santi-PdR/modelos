# Investigación de animaciones, efectos y ataques especiales

Revisión de código y documentación, no una afirmación de que las técnicas ya se hayan incorporado ni una evaluación en movimiento dentro del juego.

## Referencias antiguas

- [Mo' Bends](https://github.com/mobends/MoBends), versión histórica 1.1.0, commit `1f25e6ddbbf67e95b704149548662a6fa6d7b972`, 1.12.2. El código `AttackSlashInwardAnimationBit`, `AttackSlashDownAnimationBit` y `AttackWhirlSlashAnimationBit` coordina torso, cabeza, brazo principal, brazo libre y piernas; adapta los lados a la mano y alimenta una estela solo durante el movimiento. `SwordTrail` guarda poses previas y desvanece segmentos en vez de dibujar una imagen fija. MIT, Iwo Plaza. El modelo articulado de Mo' Bends no coincide directamente con los brazos vanilla de PlayerAnimator, por lo que no se puede copiar el movimiento sin retargeting ni validar la empuñadura.
- [Aperture](https://github.com/mchorse/aperture), 1.12.2, commit `d8d627f928e7e676837205b9fd7ac72513e92f3c`. `KeyframeFixture` separa canales de posición, yaw, pitch, roll, FOV y distancia; `PathFixture` interpola rutas y el sistema de modificadores permite seguimiento. Es una herramienta de cinemáticas, no un mod de combate ni un ataque listo para usar. GPL-3.0; estudiado como referencia, sin incorporar código.
- [Dynamic Sword Skills](https://www.curseforge.com/minecraft/mc-mods/dynamic-sword-skills/files/2495462), versión 1.7.10 de 2017: incluye Back Slice, Sword Beam y remates con objetivo fijado. El changelog menciona correcciones por golpes perdidos y selección de blanco; evidencia de que los efectos y el bloqueo del objetivo no deben sustituir a la verificación del daño. No se trasladaron código ni archivos.
- [Xaero's Special Attacks](https://www.planetminecraft.com/mod/forge164xaeros-special-attacks-v100/), versiones 1.6.4–1.8: ataques cargados e indicadores de recursos. La documentación pública permite estudiar las reglas, pero no confirma que disponga de cinemáticas o animaciones aprovechables; no se han copiado recursos.

## Referencia poco conocida, pero no antigua

- [LethalWeaponry](https://github.com/X4yii/Lethalweaponry), commit `03e3add8c7b2b418fbd2b54cbf8e709bb681c0f5`, proyecto de 2026 para 1.12.2, con una estrella al consultar. `ParticleFatalitySlash` dibuja un plano de corte orientado con escala y desvanecimiento en 15 ticks; el remate usa posición y tamaño del objetivo. El PNG examinado es una media luna roja; no se ha importado ni se ha considerado superior a los cuadros ya usados. El archivo LICENSE.txt del repositorio habla de Forge y no aclara inequívocamente el alcance de sus assets; no se atribuye una licencia a esa textura.

## Aplicación prevista a este proyecto

- **Z:** conservar el objetivo original durante preparación; para el gesto, retargetear con atención al contacto real entre mano y hoja y comprobar ambos lados en primera y tercera persona. Un brazo flotante no se arregla simplemente añadiendo partículas.
- **X:** reforzar anticipación, corte y recuperación con giro de torso y contramovimiento del brazo libre. Una estela debe acompañar la hoja y no anunciar impactos a distancia después de que el servidor ya haya causado daño.
- **C:** diferenciación de cortes, postura completa y cámara que conserve a ambos sujetos; efectos de impacto solo cuando el servidor acepta el golpe. Probar también objetivos grandes y espacios reducidos.
- Los sprites MIT de Better Combat Particle y su renderer adaptado ya tienen atribución incluida. No se usan efectos de Darkest Hours. Se conservará el origen de cualquier otro recurso y se evitará presentarlo como un recurso propio.

El ajuste de Z para guardar su marca al activarse, sin borrar otra marca obtenida durante el gesto, se verificó con un caso de dos blancos en las tres configuraciones del fixture. Las demás ideas siguen pendientes de implementación y revisión visual; una prueba automatizada no reemplaza un playtest.

## Verificación posterior del corte vertical sin Better Combat

Las capturas `confirmed_c_impact_04`, `07` y `10` se activan tras eventos `LivingDamageEvent` del objetivo de prueba; `capture-timing.tsv` registra el tick del servidor, el del cliente y el del clip. Con Better Combat instalado, el movimiento de espada elegido muestra mejor la hoja bajando hacia el objetivo. Sin sus recursos, el clip derivado de Improved Animations sigue viéndose demasiado parecido a una guardia en el momento del impacto.

Se probaron dos pistas originales de `rightItem`: inclinación y giro de muñeca. Ambas cambiaron la orientación visible pero no produjeron una postura convincente de corte, así que se retiraron. Evitar asumir que un clip se ve correcto solo porque PlayerAnimator lo parsea, avanza o porque cambia el ángulo del arma. La alternativa sin Better Combat necesita una coreografía de cuerpo y mano diseñada en conjunto y una revisión del contacto y del pivote de la empuñadura; faltan además capturas zurdas de los impactos confirmados y un playtest en movimiento.

## Corrección explícita de requisitos visuales

La revisión del usuario rechazó la guardia que cruza la cara, los brazos desconectados en primera persona y los agarres; las capturas no constituyen aprobación. El requisito es conservar **el combate y la compatibilidad de Better Combat**, pero las animaciones deben proceder de **otro mod**, no los clips predeterminados de Better Combat. Esto afecta tanto al arreglo `BETTER_COMBAT` de habilidades como a los tres primeros ataques del preset de arma; permanecen como trabajo pendiente y no satisfacen aún el requisito. La prueba de una coreografía original tampoco cumple la nueva aclaración y fue revertida. Hay que adaptar y acreditar movimientos de otro proyecto compatible, probar las transformaciones en primera/tercera persona y con ambas manos, y verificar que el hitbox y la ventana de daño de Better Combat sigan sincronizados.

Candidatos existentes: Improved Animations (MIT; adaptación de X y vertical ya en el proyecto) y Serious Player Animations (MIT; `sword_attack` y `sword_attack2` ya presentes). Su presencia no implica que el retargeting o las posturas sean correctos. Mo' Bends usa otro esqueleto y requiere adaptación, no copiar ángulos sin validación. La ejecución visual `45065244473` terminó en error aunque llegó a publicar capturas; investigar la causa antes de confiar en ella.

## Primer retarget de clips externos en Better Combat

El preset de cuatro ataques ahora referencia adaptaciones locales: `stain_serious_1/2` de Serious Player Animations y `stain_improved_3/4` de Improved Animations, con sus licencias MIT incluidas. La herramienta `adaptar_serious_bc.py` convierte rotaciones de los clips ya incluidos al formato usado por Better Combat, omite desplazamientos y ajusta keyframes al upswing original; conserva hitboxes, multiplicadores y ventanas originales. La trayectoria resultante es experimental: quitar canales y redondear ticks modifica la fuente y no garantiza sincronización en todas las configuraciones de velocidad de Better Combat. Z conserva el gesto de Emotecraft; X usa Improved Animations y C alterna Serious Player Animations e Improved Animations, sin seleccionar clips predeterminados de Better Combat.

El workflow visual `45072706666` y build `45072706618` terminaron correctamente. La prueba confirma que el cliente y las verificaciones corrieron, no que los ataques normales estén correctamente sincronizados o que las poses sean buenas. En las capturas del daño confirmado de C los golpes verticales 4 y 7 aún muestran la katana levantada en vez de cortar; el golpe 5 apunta hacia fuera del objetivo. La guardia y brazos de primera persona siguen pendientes. Hacen falta pruebas de selección real de los cuatro recursos en Better Combat, capturas durante golpes normales, corrección visual y playtest.

## Verificación real del registro y descartes posteriores

El fixture `45076866783` comprobó dentro del cliente con Better Combat que `WeaponRegistry` resuelve los cuatro IDs importados y que `AnimationRegistry` los tiene cargados; no verifica que los cuatro se ejecuten o peguen con sincronización visual correcta. Sus tres fases de render y verificación pasaron, así como la compilación `45076866765`; el workflow terminó en error en el paso de guardar imágenes por causa aún no diagnosticada, aunque publicó `698e9926`. La galería sigue mostrando problemas de guardia, brazos de Z y contacto de C.

La prueba `45075610731` de roll de guardia `0.65` y contacto de `sword_attack` en tick fuente 5 empeoró la postura: la hoja cruzaba la cara y los golpes 3/5/9 aparecían de canto, por lo que se revirtieron ambos cambios. Esos valores no deben considerarse solución. El contacto requiere revisar el pivot y la trayectoria completa del clip importado, no solo desplazar su tiempo.

## Ensayos de guardia, Z y C posteriores

- `dbafee98` compensa el roll de muñeca al abrir el brazo de la guardia: el frente diestro deja la hoja levantada al costado y ya no sobre la cara. El zurdo sigue problemático: en `00c_left_guard_front.png` la hoja queda detrás de la cabeza y la empuñadura requiere revisión. La prueba de yaw izquierdo −45 (`45335286042`) dejó la espada horizontal sobre el cuello, descartada; cambiar el pivote izquierdo a −45 (`45336699753`) dejó la hoja visible pero empeoró Z, por lo que se restauró el pivote anterior. El nuevo frame 00c permite comparar la guardia zurda de frente.
- `b65b43d3` encuadra Z moviendo el modelo completo en vez de desplazar ambos brazos por separado; `dbafee98` modera el encuadre zurdo. Aunque esto evita desplazar directamente cada hombro, las capturas zurdas aún muestran brazos flotantes y contacto dudoso. Se probó también rotar el brazo libre (`45332335876`) y se revirtió al empeorar algunas poses. No se considera Z resuelta.
- `ee527b3e` usa provisionalmente la variante Serious Player Animations que apunta hacia el blanco para los cortes horizontales de C; los impactos 3/5/9 mejoraron en capturas, pero se repite el mismo gesto. `530a36b3` transfiere la pista de muñeca del mismo mod a la adaptación vertical de Improved Animations; impactos 4/7/10 apuntan mejor al blanco. Estas son capturas inmediatamente posteriores al evento, no una prueba de movimiento o de calidad cinematográfica.
- `456b9212` serializa workflows visuales por rama para que las ejecuciones no publiquen capturas desfasadas al correr simultáneamente y exige la nueva captura zurda. El workflow `45338153503` y build `45338153577` terminaron correctamente. Falta verificar la coreografía continua, ataque completo de Better Combat, agarres, cámara y audio en juego.

Prueba posterior `45339691274`: el pivote zurdo neutro (0 grados frente a +45) hace más visible la hoja de frente, pero sigue bordeando la cara y el encuadre/agarre en Z no está aprobado. La prueba `45341219285` amplió la guardia de `.65` a `.85` radianes con compensación de muñeca; la izquierda seguía cruzando la cara y se descartó esa ampliación. Las capturas de esa ejecución conservan la postura descartada; el código regresó a `.65`. Ninguna prueba aislada sustituye animación continua ni evaluación en juego.
