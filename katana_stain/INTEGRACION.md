# Katana del Asesino de Héroes — prototipo Forge 1.20.1

> Las primeras secciones describen prototipos históricos integrados en capatest.
> La versión actual es independiente (`stainkatana`); ver las secciones finales.

Se integra en el mod existente (Forge 47.3.0, GeckoLib 4.8.1), manteniendo
el identificador `capatest` para no romper mundos ni recursos de la capa.
El nombre visible propuesto del mod es **Legados de Combate**; hay una
pestaña creativa con la capa y la katana. Comando:

```
/give @s capatest:katana_stain
```

La hoja usa el modelo editable de esta carpeta, exportado al recurso GeckoLib
con `python3 katana_stain/tools/export_forge.py`. La vaina oculta no se
exporta. Tamaño de origen aprox. 29 unidades (1.81 bloques), reducido a 72 %
en tercera persona: aproximadamente 1.30 bloques antes de transformaciones
del portador. Las poses y escala son provisionales hasta verificarlas en juego.

## Mecánica inicial inspirada en Stain

- Una espada con daño/velocidad de hierro estándar; un golpe válido marca al
  último objetivo vivo durante 10 s, solo en el servidor y en el mismo mundo.
- Clic derecho con esa espada aplica ralentización intensa durante 3 s a la
  víctima marcada si sigue viva, cargada y a 8 bloques o menos. Consume la
  marca y activa 10 s de enfriamiento. No bloquea giro ni ataques y no es una
  parálisis completa. No fuerza la carga de chunks ni rastrea entre dimensiones.
- Partículas rojas discretas al golpear y activar, sin sonidos adicionales.
  Esto es una aproximación de juego, no la reproducción exacta del don.
- El corte usa **la animación vanilla de brazo**. Los clips personalizados,
  combos y VFX de estela aún no están implementados; requieren coordinación
  cliente/servidor y pruebas en primera y tercera persona.

## Antes de considerarlo listo

Compilar con JDK 17 y Gradle 8.8 y probar el cliente y servidor dedicado de
Forge 1.20.1 con GeckoLib 4.8.1; comprobar que la capa y Curios funcionan como
antes, alineación de la katana en ambas manos, GUI, suelo y marcos. Verificar
UV, reflejos, animación vanilla, daño, durabilidad, objetivo no cargado,
PvP, expiración, distancia, cooldown y efectos en mobs y jugadores. No se
considera validado en juego hasta realizar esas pruebas.

## Icono de inventario

El icono plano se preparó a partir de la imagen proporcionada por el usuario:
se eliminó el fondo ajedrezado y se adaptó a 64×64 con transparencia. El
renderer lo usa solo en GUI; la geometría 3D sigue usándose en mano, suelo y
marco. Falta confirmar visualmente encuadre, orientación y contraste en juego.

## Prueba aislada para test-1

La variante `-PkatanaOnly` usa una entrada y recursos aislados preparados
por `python3 katana_stain/tools/preparar_test.py`; no incluye ni registra
la capa ni su integración Curios. Su mod ID es `stainkatana`, separado de
`capatest`: ambos pueden coexistir. En esta variante el comando es
`/give @s stainkatana:katana_stain`. El mod completo sigue siendo independiente.
Requiere Forge 47 para Minecraft 1.20.1 y GeckoLib Forge 4.8.1 o compatible.
Es un prototipo; las posiciones del arma y el comportamiento necesitan
comprobación visual y de juego.

## Versión independiente 0.2.0-test

- Nuevo icono derivado de la imagen suministrada, con vaina, y sin fondo.
- Z: parálisis de sangre (marca por golpe, alcance 8, 3 s, 12 s de espera).
  Aplica lentitud extrema y debilidad: no impide mirar ni garantiza bloquear
  ataques a distancia. X: corte frontal (hasta 3, 5 de daño, espera 5 s).
  C: Sentencia del Asesino (hasta 5, 9 de daño, espera 45 s). No consumen
  espera si no encuentran un objetivo válido.
- Las teclas se pueden cambiar en Controles > Katana de Stain. Se procesan
  en servidor, respetan distancia, línea de visión, equipos y PvP. Partículas
  y arcos propios diseñados con partículas vanilla, sin dependencia de VFX.
- El agarre de ambas manos se ha ajustado siguiendo una pose tipo espada;
  aún necesita calibración visual real en primera y tercera persona. No
  hay clips slash personalizados: se usa el balanceo vanilla y las estelas.

## Versión independiente 0.3.1-test

Tres efectos gráficos originales del mod: corte de ocho fotogramas, astillas
rojas de seis y pulso de ocho. Son partículas propias, no sprites ni
partículas vanilla o de otros mods. Las texturas se generan reproduciblemente
con `katana_stain/tools/crear_fx.py` (Pillow); no son capturas del juego.

La espada pasa a daño base 7 y velocidad de ataque 1,75 (antes 6 y 1,6).
X inflige 1,15 veces el ataque del portador (límite 12); C 1,6 veces
(límite 18), antes de armadura y resistencias. Z aplica un efecto propio:
velocidad anulada, ataques, habilidades e interacciones bloqueados y salto frenado;
dura 3 s en criaturas y 2 s en jugadores. La ulti aplica 0,75 s del mismo
efecto a los objetivos alcanzados. No es invulnerabilidad ni inmovilización
absoluta ante empujes, teletransporte o lógica de otros mods. Los cooldowns
siguen siendo 12, 5 y 45 s. El daño, PvP, equipo y alcance se comprueban
en el servidor. Pose de mano compensada hacia el centro del mango; ajuste
preliminar, sin evaluación en juego. No hay clips propios de brazo: se usa
el balanceo vanilla acompañado de los FX originales.

## Versión independiente 0.4.0-test

Se retiran los sprites originales del prototipo y se distribuyen fotogramas
sin modificar de Better Combat Particle, de Malfu (MIT): fuentes, revisión y
licencia en `META-INF/BETTER_COMBAT_PARTICLE_LICENSE.txt`. El adaptador de
partículas es propio y no reproduce el renderer ni las animaciones de ese mod;
no se afirma que tenga su mismo aspecto en juego. Se cambia el shader del
icono a uno emisivo, se ensaya otra pose de tercera persona, y se acorta el
nombre y el tooltip. Estos cambios aún requieren prueba visual en cliente,
incluyendo ambas manos, primera persona, iluminación y las tres habilidades.

## Versión independiente 0.5.0-test

Requiere también `player-animation-lib-forge-1.0.2-rc1+1.20` (PlayerAnimator)
instalado en cliente y servidor. No se incluye la biblioteca en el JAR.
La confirmación del servidor activa las animaciones del jugador para el propio
jugador y los clientes que lo observan; una habilidad rechazada no anima.
Se reutilizan `sword_attack`, `sword_attack2` y `eating_right` de Serious
Player Animations de McVader (MIT), desde el port de avectus, revisión
`5ff26dbfc7d9fcea984ea49c7f380ed52a2ff28e`. Se cambió `loop` a `false`
en `eating_right` para que la parálisis no deje una animación infinita.
Licencia incluida en `META-INF/SERIOUS_PLAYER_ANIMATIONS_LICENSE.txt`.
Son movimientos reutilizados, no animaciones específicas de Stain; el gesto
para Z es una aproximación. Daño y efectos siguen siendo instantáneos en el
servidor, no sincronizados a un fotograma concreto. La vista en primera persona,
poses y compatibilidad con otros mods requieren comprobación en cliente.

## Versión independiente 0.6.0-test — secuencia y fuente de animaciones

- Al iniciar una habilidad con objetivo válido se envía su animación; el
  servidor revalida y ejecuta el impacto después (Z: 2 ticks; X/C: 7 ticks),
  y bloquea nuevas habilidades durante la recuperación. El enfriamiento se
  consume al iniciar, aunque el objetivo escape o la acción se interrumpa.
  Si se cambia de arma, dimensión, muere el jugador o sufre parálisis, se
  cancela la acción pendiente. La marca de Z no puede cambiar de víctima a
  mitad de preparación. Salida del jugador y parada del servidor limpian estado.
- Si está instalado **Better Combat para Forge 1.20.1**, se leen directamente
  de sus recursos las animaciones de katana `two_handed_slash_horizontal_right`
  y `two_handed_slash_vertical_right` de Daedelus para X y C, respectivamente.
  No se redistribuyen ni modifican sus archivos. Si no están disponibles se
  usan los clips de Serious Player Animations ya incluidos; Z usa su gesto
  modificado de comer. Better Combat no es obligatorio y agrega sus propias
  mecánicas al juego: instalarlo es una elección del usuario.
- Se habilitó el modo de brazos de tercera persona de PlayerAnimator durante
  la vista en primera persona. Ni esta integración, ni los tiempos exactos de
  contacto de cada clip, ni su aspecto con este modelo y otros mods han sido
  probados visualmente. El retraso de red también puede desfasar las vistas.
  Esto es una base técnica de prueba, no una validación de calidad profesional.

## 0.7.0-test — Better Combat 1.9.0+1.20.1

Verificada la fuente de la versión exacta, commit `8814f0297bb85f4513646e73d604069487ce7322`:
Better Combat inicia sus animaciones en el tick 0, no en `beginTick` como se
había indicado en 0.6.0. Se corrige ese error, se acelera la reproducción,
se añaden transiciones, prioridad sobre la capa de golpes de Better Combat y
espejado para jugadores zurdos. La ulti combina dos cortes de Better Combat;
sus impactos, separados, hacen cada uno aproximadamente la mitad del daño
anterior y se vuelven a validar en servidor. El cooldown empieza al iniciar.
Para golpes normales se añade un archivo de compatibilidad que hereda el
preset `bettercombat:katana`: con Better Combat son golpes y pose a dos manos.
Sin Better Combat, los clips incorporados siguen siendo el respaldo.

Estas son mejoras técnicas basadas en fuentes reales, no una verificación
visual: todavía deben probarse agarre, primera/tercera persona, tiempos,
compatibilidad de las dos capas, escudos y las tres habilidades en el cliente.

## 0.8.0-test — proporción, marcas y VFX

- El modelo original mide aproximadamente 28,7 unidades; la escala en mano
  sube de 0,72 a 0,82 en tercera persona (unos 1,47 bloques frente a 1,8 del
  jugador) y de 0,68 a 0,74 en primera. No se ha alterado la geometría base.
  Son proporciones de juego, no una medida canónica del arma. Las poses aún
  necesitan prueba en cliente, también durante las animaciones a dos manos.
- Se adapta el plano orientado y de doble cara de Better Combat Particle, de
  Malfu, junto con sus fotogramas existentes y licencia. Los cortes pasan de
  ser siempre billboards a orientarse por el yaw del atacante y se tiñen de
  acero rosado y rojo oscuro; la parálisis tiene un trazo carmesí. Los efectos
  siguen siendo adaptaciones: no son toda la implementación original del mod.
- Los impactos válidos de X/C marcan a la primera víctima viva, igual que un
  golpe normal, de modo que Z puede usar esa marca. Se mantiene la validación
  en servidor y la revisión del objetivo al impactar. El texto se acortó.
- Esta versión compila y debe probarse en cliente para evaluar contraste,
  orientación, escala, agarre, sincronización y coste visual. Ninguna prueba
  automática sustituye capturas o vídeo de la partida.

## 0.9.0-test — gesto y pruebas de secuencia

Z usa `Inspect`, una animación de inspección de objetos de Overseer, de la
colección Emotecraft-emotes (CC0); se incluye con espacios normalizados y se reproduce a
mayor velocidad. Es un gesto de inspección, no una reproducción literal del
lamido de sangre de Stain. El impacto de parálisis pasa al tick 8 para dar
preparación al gesto. Fuente y licencia en `META-INF/EMOTECRAFT_*`.

La secuencia de habilidades se ha aislado en `AbilityTimeline` y se prueba
con Java para los tres tiempos, repetición, salto de ticks y cancelación. Un
arma rota durante el primer impacto cancela el resto. Los cortes muestran sus
trazos al impactar incluso si el objetivo escapó durante la preparación; no
hay daño ni desgaste si no golpean. Las pruebas no cubren el aspecto visual,
el combate de Better Combat instalado ni una partida real de cliente.

## 0.10.0-test — encuadre de la ulti

La ulti confirmada inicia para su propio jugador una secuencia breve de bandas
y reducción suave del FOV, adaptada del mod Cinema Scope de heconis / port de
ChopstickGuy (MIT, licencia en `META-INF/CINEMASCOPE_LICENSE.txt`). No es una
cinemática de cámara libre: no cambia la perspectiva, no inmoviliza al jugador,
no oculta el HUD ni altera la velocidad del mundo. El servidor sigue resolviendo
los impactos. Se cancela al interrumpirse la habilidad, al salir del mundo o por
límite de seguridad, y se pausa con el juego. Solo el atacante ve las bandas;
los demás siguen viendo animación y partículas sincronizadas.

Se puede desactivar o ajustar en `config/stainkatana-client.toml`, sección
`ultimate_scene`: `enabled`, `barFraction`, `zoomFraction`. Valores 0 eliminan
barras/zoom respectivamente. El sonido de los cortes usa el evento registrado
por Better Combat `bettercombat:katana_slash` si existe; sin ese mod se usa un
sonido vanilla. No se redistribuye audio de Better Combat.

Es una primera prueba de encuadre: no se ha verificado en el cliente ni con
otros mods de cámara, FOV, HUD o shaders. Las pruebas de curva, compilación y
servidor no certifican calidad visual ni sincronización real.

## 0.11.0-test — dos cortes diferenciados

Se revisaron los clips de Better Combat 1.9.0: el primero de la ulti es
`two_handed_slash_vertical_right` y el segundo es
`two_handed_slash_horizontal_left`; el ataque simple usa
`two_handed_slash_horizontal_right`. El segundo arco horizontal se orienta al
revés del primero y se invierte para jugadores zurdos, como las animaciones;
el primer arco diagonal también invierte su inclinación. Se siguen utilizando
los sprites de Better Combat Particle atribuidos previamente. Son ajustes de
orientación estimados, no una trayectoria calculada desde la hoja.

Cada corte de la ulti envía desde el servidor un evento visual que produce un
suave pulso adicional de FOV únicamente en el jugador atacante, durante el
encuadre y solo si está activado. No es un efecto de cámara para los objetivos
ni altera el daño. Desactivar la escena o poner `zoomFraction = 0` elimina el
pulso. Los paquetes de red son ahora versión 6: cliente y servidor deben usar
la misma versión. La latencia, el agarre, las direcciones y la compatibilidad
con mods de cámara siguen requiriendo prueba visual; no se garantiza que los
planos del efecto coincidan exactamente con la hoja.

## 0.12.0-test — revisión de hoja, acción y comodidad

- La hoja editable conserva su curvatura, sus mellas reales y la guarda compacta.
  Se aclararon únicamente las dos islas UV del plano principal del acero y se
  redujo un poco el grosor de tres cubos en la punta. La geometría y textura de
  la katana aislada se exportan ahora directamente a `stainkatana`, sin tocar
  los recursos de `capatest`. `verificar_modelo.py` vuelve a abrir el archivo,
  comprueba la textura embebida y compara los 82 cubos visibles con GeckoLib.
  `vistas/modelo_comparacion.png` muestra tres vistas de software junto a la
  referencia aportada; no reproduce la iluminación ni la mano de Minecraft.
- Anatomía estudiada: sori, shinogi, kissaki y habaki; la referencia de Stain
  tiene prioridad sobre reconstruir una katana histórica exacta. Guía consultada:
  https://www.hanbonforge.com/blog/Japanese-Sword-Terminology
- El gesto de Z es el mismo `Inspect` CC0 de Overseer pero pasa de 4x a 3x; su
  contacto se mueve de tick 8 a 9, la salida al 18 y recuperación al 21. Es un
  gesto de inspección, no una animación literal de lamer sangre. X y C conservan
  los clips Better Combat cargados de la instalación y sus impactos al tick 7
  de cada golpe. No se redistribuyen los clips ni su audio.
- La ulti agrega un ligero giro visual de cámara alternado en cada golpe,
  superpuesto al FOV y las bandas de Cinema Scope. No cambia el apuntado ni
  fuerza tercera persona. `impactRollDegrees` permite 0–2 grados; por defecto
  0,65; `enabled = false` desactiva el encuadre completo. Se estudió Slashh
  (https://github.com/shuttheirprayer/slashh, revisión
  `6a5900eaded205968c6fbebc3b3fe632c8e5fb9a`): señales de impactos, límites y
  controles de comodidad; no se copian sus recursos ni su código. Las
  partículas siguen siendo los recursos MIT de Better Combat Particle.
- En PvP, parálisis de sangre baja de 40 a 30 ticks, y la breve detención de
  cada corte de la ulti de 15 a 10 ticks; contra mobs pasa de 60 a 50 ticks en
  Z y permanece 15 en C. El daño sigue siendo servidor y limitado: con 7 de
  daño de atributo, X inflige 8,05 y C 5,6 por corte antes de armadura; caps
  de 12 y 9 respectivamente. Los enfriamientos son 12, 5 y 45 segundos.
  La marca dura 10 segundos. La red usa protocolo 7, por lo que cliente y
  servidor necesitan 0.12.0-test. Son valores iniciales, no balance validado
  mediante partidas. La descripción ahora explica las funciones sin teclas.

Pruebas automatizadas no demuestran que el agarre, la orientación de VFX,
la animación en primera persona, los tiempos con latencia o la cámara se vean
bien. Sigue siendo una escena de combate con cámara local, no una cinemática
con cámara autónoma. Es necesaria una prueba en cliente y con otros mods.

## 0.13.0-test — prueba visual en cliente

Se añadió un escenario **solo para CI**, no incluido en el JAR, que arranca
Forge 1.20.1 en Xvfb/Mesa con GeckoLib y PlayerAnimator, equipa el arma, coloca
un husk inmóvil y activa las tres habilidades contra él. Se toman capturas
reales de inventario, primera y tercera persona y momentos del combate en
`vistas/client-test/`. El escenario carga temporalmente los tres JSON originales
para las animaciones de Better Combat 1.9.0 desde su repositorio; **el mod
Better Combat no está instalado en esa prueba**, por lo que esta prueba no
verifica su integración ni la interacción entre los dos mods. Esas animaciones
no se empaquetan ni redistribuyen en nuestro JAR. Por la baja tasa de cuadros
virtual, algunas capturas cercanas pueden saltarse; no son un vídeo ni una
prueba de sincronización exacta.

En las imágenes se observó la punta de primera persona recortada y el plano del
corte horizontal casi de canto. Se bajó la escala de primera persona de 0,74 a
0,64 sin modificar la tercera persona, se inclinó el plano del corte y se
agrandaron moderadamente los arcos conservando los sprites de Better Combat
Particle. La escena y los arcos **siguen sin estar terminados ni validados por
un jugador**: las fotos muestran que aparecen, pero no prueban que sean épicos,
que coincidan con la hoja en todas las orientaciones o que el agarre, zurdos,
sonidos, efectos de pantalla, rendimiento o compatibilidad funcionen bien.
Una revisión completa requiere vídeo/observación en cliente con el Better Combat
Forge 1.9.0 real y los demás mods de la instancia.

El cliente de desarrollo necesitó remapear los refmaps de PlayerAnimator para
arrancar con Mojmap; el ajuste está limitado al perfil `-PkatanaVisual`. No
implica que los usuarios finales deban cambiar nada. El JAR de producción no
incluye clases del escenario visual ni los JSON descargados para la prueba.


## 0.14.0-test — cambios para la prueba solicitada

- Stain Blade aparece solo en la pestaña del mod; el tooltip no enumera teclas
  ni habilidades. GeckoLib y PlayerAnimator siguen siendo dependencias; Better
  Combat es opcional. Si no están disponibles sus clips se usan los de reserva.
- HUD a la derecha al sostener la katana: teclas reasignables y tiempo restante.
  El servidor decide la aceptación y manda los tiempos al activar y cada segundo;
  un `--` indica que todavía no llegó la sincronización. La ventana cinematográfica,
  el HUD y el tinte rojo pueden desactivarse en la configuración del cliente.
- Z requiere marcar con un golpe, consume la marca al paralizar y concede fuerza II
  y velocidad II durante ocho segundos; el rojo aparece solo si se aplica la
  parálisis. X y C golpean objetivos delante del jugador. C dura 46 ticks y tiene
  dos impactos; efectos y daño siguen validados por el servidor. Enfriamientos:
  Z 6 s, X 3 s y C 18 s. Daño X = 2,2 × atributo (límite 26); cada corte C =
  2,8 × atributo (límite 36), antes de armadura y otras reglas del juego. PvP
  tiene duraciones de inmovilización menores. Son valores intencionalmente fuertes.
- Se ajustó la iluminación del icono suministrado y la orientación de tercera
  persona; las capturas CI son vistas puntuales, no demuestran que el agarre sea
  correcto con todas las perspectivas, skins y otras modificaciones.
- `vistas/client-test/` usa los JSON de clips de Better Combat, sin instalar el
  mod completo; `vistas/client-vanilla/` prueba el arranque y clips de reserva
  sin dichos JSON. Ninguna ejecución demuestra compatibilidad real con Better
  Combat instalado, ni calidad cinemática o sincronización en una partida real.
  El gesto de Z aún es un clip de inspección adaptado, no un lamido literal;
  los VFX usan los sprites MIT de Better Combat Particle, no efectos vanilla.
  La secuencia es encuadre local con dos cortes, no una cinemática autónoma.


## 0.15.0-test — animación de ataques normales

Sin Better Combat, observamos el swing vanilla ya sincronizado y reproducimos
clips alternos MIT de Serious Player Animations; no modificamos alcance ni daño.
No se interrumpe una habilidad activa para poner el swing. Con Better Combat
instalado el observador se desactiva para no pisar sus animaciones normales.
La prueba visual también intenta cargar Better Combat Forge 1.9.0 y Cloth Config
como dependencias exclusivamente de CI, sin incluirlas en el JAR. Un arranque
y capturas automáticas no reemplazan una partida, una revisión de ambos brazos
o probar interacciones con otros mods de animación.

## 0.15.0-test — prototipo de escenas dirigidas

- X se puede activar sin objetivo; busca blancos válidos hasta 7 bloques, en un
  cono frontal y con visión directa. Los trazos avanzan a lo largo del alcance.
- Z consume una marca de sangre de hasta 10 s de antigüedad a hasta 24 bloques,
  siempre que el blanco siga cargado, visible y sea legal. Se muestran motas
  personalizadas alrededor del inmovilizado. Cada segunda Z exitosa desencadena
  automáticamente tres dagas visuales 3D y tres intentos de daño del servidor;
  no son entidades ni proyectiles físicos. Si el blanco deja de ser válido, la
  secuencia termina. El contador se conserva en los datos del jugador.
- C escoge el mob legal más cercano dentro del cono y 15 bloques: nunca elige
  jugadores ni ítems. Su secuencia dura 200 ticks (10 s a 20 TPS) y aplica hasta
  diez cortes. Solo el último puede rematar al mob; otros daños sí pueden
  matarlo antes. Se cancela si cambia la katana, muere o se desconecta el
  portador, el blanco desaparece/se aleja o se bloquea la línea de visión.
  El efecto de sujeción dura como máximo 12 ticks y se renueva, sin cambiar
  permanentemente la IA; se retira al cancelar. No inmoviliza a los jugadores.
- El HUD fue redibujado; el icono es una interpretación pixel-art de la imagen
  suministrada, adaptada para ser más legible a 16px. El modelo usa una capa
  roja emisiva; no es bloom ni ilumina el entorno. El arma no se modificó en
  geometría, solo su transformación de primera persona.
- El cliente visual de CI inicia tres escenarios: clips externos aislados,
  fallback sin Better Combat y Better Combat Forge 1.9.0 completo con Cloth
  Config. Comprueba diez segundos de sujeción, daño, dagas tras la segunda Z,
  X al aire, C a 14 bloques, cancelación y Z a 20 bloques. Las pruebas ocurren
  en un único mundo local con un husk; no prueban todos los mobs, latencia,
  multijugador, PvP o los otros mods de la instancia.
- Las escenas usan encuadre local y clips de PlayerAnimator/Better Combat,
  no una cámara autónoma con coreografía o cambio real de perspectiva. En las
  capturas, el brazo en reposo de primera persona no aparece y la posesión en
  Better Combat aún debe juzgarse con el jugador y sus mods; no se garantiza
  que se haya resuelto el agarre reportado. Las dagas son un primer modelo y
  efecto, no un recurso profesional evaluado por un artista. Falta mejorar y
  evaluar la calidad de la escena en movimiento y sus ángulos.
- Red de protocolo 9: servidor y cliente deben usar la misma versión de este
  mod. Los recursos de Better Combat y Cloth Config de las pruebas no se
  incluyen ni se redistribuyen dentro del JAR.

## 0.16.0-test — prototipo en revisión

- Icono: se usa la imagen proporcionada por el usuario, quitando únicamente el fondo blanco exterior y escalando para la interfaz.
- Z acumula hasta dos cargas en el servidor; el siguiente ataque válido inicia el remate detrás del blanco, si hay espacio seguro y visible. El daño es alto pero no es una ejecución garantizada. Se consumen al iniciar, no cuando se pulsa Z.
- C conserva el blanco mob a 15 bloques y la duración de 200 ticks. El servidor comprueba posiciones con suelo, colisión, visibilidad, borde del mundo y chunks cargados; coloca al jugador cerca del objetivo y cambia de posición entre golpes cuando es seguro. Si no hay acceso inicial, no inicia. El cliente usa una cámara orbital local con raycast; si no puede acceder a la cámara vuelve al encuadre normal.
- Los movimientos propios de respaldo tienen 4 cortes básicos y 10 poses para C; con Better Combat, la C usa clips disponibles del mod instalado y sus ataques básicos usan el preset de cuatro pasos. El daño extra del cuarto golpe sin Better Combat depende de cuatro impactos con carga suficiente dentro de la ventana de combo; los swings al aire son visuales y no cuentan para daño.
- Efectos de corte: se mantienen sprites de Better Combat Particle (Malfu), atribuidos en el mod. No se incorpora arte ni efectos de Darkest Hours. El análisis estático de su ulti Infinite Mirage identificó pasos servidor (bloqueo, movimientos, golpes) y cámara cliente por poses y órbitas; no es una prueba de juego ni una copia de dicha implementación.
- Limitaciones: la cinematográfica usa cámara interpolada en torno al objetivo, no una recreación de la secuencia de Darkest Hours; sus poses nuevas son prototipos y no captura de movimiento. La prueba gráfica automatizada no sustituye una revisión humana de movimiento, agarre y comodidad. El remate con Better Combat se prueba en el fixture mediante un evento de ataque simulado, no por una sesión multijugador real. El protocolo de red es 10: cliente y servidor deben usar el mismo JAR.

## 0.17.0-test — revisión experimental de agarre y jefes

- Con dos marcas de Z acertadas, volver a pulsar Z inicia el remate si hay un destino seguro detrás del último objetivo (o un objetivo cercano visible). Los ataques normales ya no lo consumen. El daño base se limita a un máximo del 75% de la vida máxima y no más de la vida actual menos uno; los modificadores o reglas de terceros pueden alterar el resultado final.
- C busca entidades vivas no jugadoras por su caja de colisión y contempla piezas multiparte Forge. Su contención no depende de que el jefe acepte el efecto de poción; al cancelar se libera. La prueba automatizada selecciona, sujeta y libera un Ender Dragon en un entorno controlado, no garantiza compatibilidad universal con todos los jefes o ataques de terceros.
- Se ajustaron por separado las transformaciones de agarre de primera y tercera persona; se requiere revisión humana, especialmente durante animaciones y con otros mods. El cuarto golpe de Better Combat usa un corte vertical de su instalación en vez del slam; sin Better Combat usa un clip alternativo de Serious Player Animations, atribuido.
- La cámara C recorre varias posiciones suavizadas, y comprueba obstáculos; es un diseño propio basado en el análisis estructural de las escenas de Darkest Hours, no sus recursos ni su coreografía. El visualizador usa recursos de Better Combat Particle, no de Darkest Hours.


## 0.18.0-test — versión para prueba en juego

- El remate se activa pulsando Z tras dos parálisis exitosas. La selección y el
  daño se resuelven en el servidor; el golpe bruto está limitado a 60 puntos,
  el 90 % de la vida máxima y la vida actual menos uno. Armadura, resistencias
  y modificaciones de terceros alteran el daño real. Si no hay una posición
  segura detrás, no consume las cargas y muestra un aviso.
- Los desplazamientos usan una adaptación acreditada de SlashBlade: Resharped;
  se buscan varias alturas y no se fuerzan chunks ni se atraviesan obstáculos.
  C sigue pudiendo comenzar sin mover al jugador cuando no hay suelo seguro.
- La cámara de C suaviza sus movimientos en función del tiempo entre fotogramas;
  los ataques incluyen efectos y sonidos, con animaciones de Better Combat cuando
  están disponibles y alternativas si no lo están.
- Las pruebas automáticas cubren las tres configuraciones del fixture, el remate
  por Z y la selección, contención y liberación del Ender Dragon controlado. No
  son una partida real ni garantizan compatibilidad con todos los jefes custom.
- Limitaciones conocidas: el agarre zurdo en tercera persona necesita ajustes;
  el gesto de sangre todavía no recorre claramente la hoja, y las proporciones
  de los brazos en primera persona requieren revisión. Sonidos y movimiento no
  han sido evaluados auditivamente ni mediante una partida humana.
- Misma versión en cliente y servidor; no incluye la capa ni los clips de Better
  Combat, Ultimate Battle o Darkest Hours. Requiere Forge 1.20.1, GeckoLib 4.8.1
  y Player Animator Forge 1.0.2-rc1 o compatible. Better Combat es opcional.

### Optimización de texturas (trabajo en curso)
La textura editable del modelo se conserva a 512 × 512 en el `.bbmodel`; la
exportación de juego la reduce a 256 × 256 con muestreo vecino. El espacio UV
de GeckoLib sigue siendo 512 × 512. El icono y las partículas de juego se
reducen a 64 × 64; la daga ya era 16 × 16. Para regenerar el modelo se necesita
Pillow (`python -m pip install Pillow`); `tools/optimizar_texturas.py` es
idempotente, y `tools/preparar_icono.py` regenera el icono desde el original.
La mejora potencial es de área de texel, no una medida de VRAM del juego: los
atlas, mipmaps y otros mods también influyen. Falta comprobación visual real.
En estas 21 imágenes, sin contar la daga, se pasa de 835.584 a 208.896
texeles (un cuarto). A cuatro bytes por texel serían aproximadamente 3,19 MiB
frente a 0,80 MiB antes de atlas, mipmaps, compresión y otras copias: no es una
medición del consumo real de Minecraft ni de los demás mods.

El HUD de prueba se coloca abajo a la izquierda para no tapar el arma en primera
persona; `interface.hudLeft=false` lo cambia a la derecha y `showHud=false` lo
oculta. Una vez cargadas las dos marcas, Z muestra «REMATE» aunque el cooldown
anterior siga contando, porque el servidor permite ese uso de la habilidad.

### Prototipo de coreografía posterior a 0.18
C conserva la selección y el daño autoritativos del servidor, pero el ritmo de
sus diez impactos ya no es uniforme. Los desplazamientos seguros se intentan
antes de la preparación del golpe, no en el mismo tick del impacto; si no hay
posición válida se permanece en el sitio. La cámara recibe el objetivo desde
el inicio. El gesto Z y sus ajustes de primera persona siguen siendo prototipos
para revisión visual; las capturas no demuestran contacto exacto con la hoja.

La comparación adicional del gesto con una traslación lateral del brazo y menor
profundidad en primera persona produjo mayor oclusión y no demostró contacto con
la hoja; se descartó ese experimento. Persiste la limitación visual del gesto,
por lo que la prueba automatizada no debe interpretarse como aprobación estética.

### Selección de objetivos multipartes
Al activar C se consulta también la colección de partes cargadas de Forge: si
una parte está en el área de búsqueda, se comprueba el objetivo principal por
alcance, dirección, visibilidad y legalidad. No se cargan chunks por esta
consulta. El fixture fuerza una parte de Ender Dragon en alcance con el cuerpo
principal fuera del área, además de comprobar su liberación. Esto no garantiza
compatibilidad con jefes que implementan protección o partes de otra manera.

La comparación de un ajuste separado de profundidad para la mano libre en
primera persona pasó el fixture, pero dejó la mano fuera de cuadro durante gran
parte del gesto. Se descartó y se conservaron las capturas del ajuste anterior;
la prueba funcional por sí sola no valida la coreografía.


## 0.19.0-test — candidata para prueba en juego

Versión de prueba, no una versión definitiva. Incluye el HUD desplazable, las
texturas de menor resolución, el ajuste de primera persona en reposo, el nuevo
ritmo de C y su búsqueda de partes de jefes cargadas. También gira la hoja
únicamente durante el gesto de sangre; se basa en Inspect de Emotecraft (CC0)
y utiliza partículas de Better Combat Particle (MIT), no efectos de Darkest
Hours. El renderer y agarre normales en tercera persona no se han cambiado.

El fixture Forge ha comprobado jugador diestro y zurdo, con y sin Better Combat,
el remate por Z, C sobre un Ender Dragon y la selección de una parte cuando el
cuerpo del dragón queda fuera de la caja de búsqueda. No prueba todos los mods,
latencias, jefes ni demuestra que el gesto toque la hoja. En capturas la hoja se
acerca a la cara, pero la mano libre aún no recorre claramente el filo; el
encuadre y los sonidos deben juzgarse en una partida real. Cliente y servidor
necesitan el mismo JAR y se mantienen las dependencias indicadas para 0.18.

### Efectos en desarrollo posteriores a 0.19
Los estilos visuales se separan de la cámara: el encuadre inicial ya no simula
un impacto; los golpes normales, la parálisis, el remate y el último corte de C
reciben señales distintas. Se reutilizan los sprites existentes de Better
Combat Particle (MIT, atribuidos), con una ráfaga limitada y curvas de aparición
y desvanecimiento; no se agregan texturas de Darkest Hours. Para el anillo se
incorporan siete fotogramas adicionales de `topslash360`, a 64 × 64: 28.672
texeles adicionales (aprox. 112 KiB RGBA antes de atlas y mipmaps).
Los cambios son cosméticos y el servidor conserva el control del daño y objetivos.
La versión de protocolo para estos cambios es 11: cliente y servidor deben usar
el mismo JAR. Las capturas del fixture aún requieren revisión humana y no son
una prueba de rendimiento en el modpack real.

### Prueba posterior: señales de ataque y gesto

Se suavizó la entrada y salida del desplazamiento de la mano libre durante Z,
se reajustó el encuadre de primera persona y se corrigió el agarre zurdo de
tercera persona. Desactivar `interface.vanillaSwings` ahora desactiva la
animación alternativa sin suprimir sus señales de sonido y partículas; con
Better Combat instalado, ese mod sigue controlando sus sonidos de ataque.
El fixture comprueba la señal con la animación desactivada en modo vanilla.

La compilación y las pruebas automatizadas no sustituyen una partida real:
el contacto de la mano con la hoja, especialmente en zurdos, y la calidad
del audio y del movimiento aún requieren evaluación humana. No se distribuye
audio de Better Combat: las habilidades usan su sonido si está instalado o
un sonido vanilla alternativo. No se usan efectos de Darkest Hours.

En una revisión posterior se desplazó la mano libre zurda en primera persona
hacia la hoja durante el gesto de Z. Se compararon ajustes en el mismo tick del
clip y se comprobó el resultado en tres configuraciones del cliente. Sigue
siendo una aproximación: las capturas no demuestran contacto tridimensional
exacto ni calidad del movimiento durante una partida.

## 0.20.0-test — guardia y encuadre

La instalación de esta prueba se dirige a la carpeta de la instancia, no a
`.minecraft/mods` por defecto. El número de versión y el nombre del JAR se
incrementaron para diferenciarla de las pruebas anteriores.

- Con Better Combat la katana usa una guardia propia más alta; se ajustó también
  el giro de la hoja zurda. Sin Better Combat no se impone esa guardia.
- Se reajustó el encuadre de X en primera persona para que el arma no quede
  oculta durante el impacto; se revisaron ambas manos en capturas.
- La apertura de C usa una velocidad distinta para acercar su golpe visual al
  tick de impacto del servidor. El resto de cortes conserva su velocidad.
- Z conserva el gesto e interpolación de la prueba anterior; no es un rediseño
  completo. Siguen pendientes una revisión en movimiento y del audio en juego.

Las capturas y las pruebas automáticas no garantizan contacto perfecto, estética
final, ni sincronización exacta bajo latencia. No se usan efectos de Darkest Hours.
