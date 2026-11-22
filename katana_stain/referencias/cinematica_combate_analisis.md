# Investigación de presentación de combate (revisión en curso)

- [Epic Fight](https://github.com/epic-fight/epicfight), rama 1.20.1, commit `5c7f6e796a9ee239ffc59b812e15368a1038c34c`: `AttackAnimation` divide cada fase en anticipación, preparación, contacto y recuperación; `EpicFightCameraAPI` separa seguimiento/cámara de la orientación del jugador y comprueba visibilidad y rango. Su código está bajo GPL-3.0 y versiones recientes indican que sus assets son All Rights Reserved. Se estudiaron conceptos; no se ha copiado su código ni sus recursos.
- [SlashBlade: Resharped](https://github.com/0999312/SlashBlade_Resharped), commit `6e2a0a092fb794d7ea56fd83452869674f3ab1c7`, código MIT: `ComboStateRegistry` programa acciones de corte en ticks concretos y `AttackManager` orienta y posiciona los efectos con el ataque. Se estudió la sincronización como referencia; no se copiaron modelos, texturas ni sonidos. El código de teletransporte previamente adaptado conserva su atribución en el mod.
- [Devil Mine Craft](https://www.curseforge.com/minecraft/mc-mods/devil-mine-craft) describe una combinación de coreografía de cámara, animación, estelas y sonido para sus remates; su licencia figura como All Rights Reserved. Solo se consultó la descripción pública, sin incorporar recursos.
- [Better Combat Particle](https://github.com/MalfuXT/malfu-mods-bc_slash_particle-1.20.1) aporta los cuadros de anillo ya incorporados y atribuidos bajo MIT; se mantiene sin depender de Darkest Hours.

## Aplicación y límites

El experimento actual encuadra a atacante y objetivo desde un lateral relativo al eje entre ambos, en lugar de una órbita completa que podía tapar al jugador detrás del enemigo. El remate corto de Z usa su propia duración, en vez de reproducir únicamente el principio de una toma de 200 ticks. Se mantienen la interpolación, el raycast contra paredes y los disparadores de impacto decididos por el servidor. El foco inicial ya no dispara un pulso de impacto falso.

Esto no es una validación estética ni demuestra compatibilidad con Epic Fight o Devil Mine Craft. Hay que revisar las capturas reales, sobre todo durante los teletransportes y con enemigos grandes, obstáculos, ambas manos, primera persona y la cámara restaurada; después hace falta un playtest del usuario. La pose de guardia y las animaciones de Z/X/C continúan en revisión.
