# Katana del Asesino de Héroes — prototipo Forge 1.20.1

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
