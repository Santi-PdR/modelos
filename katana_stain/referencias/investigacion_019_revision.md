# Revisión de la prueba 0.19: investigación y límites

## Interfaz
- El panel de habilidades no debe ocupar la zona del chat ni la zona inferior derecha usada por Darkest Hours. La propuesta es centro-derecha por defecto y una alternativa centrada arriba, elegible en configuración, porque un scoreboard también puede ocupar el centro-derecha.
- Las recomendaciones de diseño HUD consultadas priorizan contraste en escenas claras y oscuras, jerarquía, temporizador numérico además de barra/color y posición configurable. Referencias: https://rocketbrush.com/blog/designing-practical-and-pretty-hud-in-video-games y https://playmobile.online/designing-cooldown-ui-systems-that-feel-responsive/ . Son principios de diseño, no validación de este HUD.

## Animaciones y sonido
- Better Combat, https://github.com/ZsoltMolnarrr/BetterCombat (consultado en d7ad3c27841f70b3bb4ebbbdfa11dace17c3d09d), contiene movimientos `player_animations` y sonidos diferenciados incluyendo `katana_slash`. Su archivo LICENSE dice All Rights Reserved: no se incorporan sus recursos al repositorio. Se pueden usar como referencia y, si el usuario ya lo tiene instalado, solicitar el sonido registrado por el mod.
- SlashBlade: Resharped, https://github.com/0999312/SlashBlade_Resharped, declara MIT para el proyecto y utiliza secuencias VMD, además de ofrecer integración con PlayerAnimator. Sus movimientos muestran una dirección distinta a los cortes genéricos, pero el formato y la procedencia/licencia de cada recurso concreto necesitan revisión antes de convertir o distribuirlos. El código de teletransporte ya adaptado incluye atribución independiente.
- Simple Katanas, https://github.com/Morris-23/Simple_Katanas, declara MIT y describe parries y señales audiovisuales, pero el repositorio consultado es Fabric 1.21.1; no se asume compatibilidad con Forge 1.20.1 ni que todos los sonidos descritos estén presentes.
- Superior Combat Sounds, https://www.curseforge.com/minecraft/mc-mods/superior-combat-sounds, anuncia Forge 1.20.1 y licencia MIT, pero no se ha podido verificar la licencia y procedencia de cada muestra en un repositorio fuente accesible. No se copian sonidos solo a partir de la ficha del proyecto.
- Los sprites Better Combat Particle y el gesto Emotecraft ya integrados tienen atribuciones en META-INF; no se usan efectos de Darkest Hours.

## Verificación que aún hace falta
Las capturas en software no demuestran agarre palma-empuñadura en movimiento ni audio, y no prueban compatibilidad universal de jefes. La cinemática, cambio de ítem, daño recibido, temporización de impactos, y ambos modos de HUD requieren pruebas reales en cliente/servidor; la integración con mods de animación puede alterar el resultado.

- Improved Animations, https://github.com/ProjectSlenders/Improved-Animations, commit `9371f058d3b29e25bce6ef67ec1ea416dac0e4b1`, MIT (copyright Adam-dawoud): se adaptaron las curvas de brazos y giro de torso de `attack_sword.json` para probar un corte X propio. Se excluyeron traslaciones y canales no compatibles; la adaptación se genera con `tools/adaptar_corte.py` y requiere revisión visual y sincronización en juego. Licencia incluida en META-INF.
