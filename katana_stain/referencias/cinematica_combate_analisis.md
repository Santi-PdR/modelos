# Investigación de presentación de combate (revisión en curso)

- [Epic Fight](https://github.com/epic-fight/epicfight), rama 1.20.1, commit `5c7f6e796a9ee239ffc59b812e15368a1038c34c`: `AttackAnimation` divide cada fase en anticipación, preparación, contacto y recuperación; `EpicFightCameraAPI` separa seguimiento/cámara de la orientación del jugador y comprueba visibilidad y rango. Su código está bajo GPL-3.0 y versiones recientes indican que sus assets son All Rights Reserved. Se estudiaron conceptos; no se ha copiado su código ni sus recursos.
- [SlashBlade: Resharped](https://github.com/0999312/SlashBlade_Resharped), commit `6e2a0a092fb794d7ea56fd83452869674f3ab1c7`, código MIT: `ComboStateRegistry` programa acciones de corte en ticks concretos y `AttackManager` orienta y posiciona los efectos con el ataque. Se estudió la sincronización como referencia; no se copiaron modelos, texturas ni sonidos. El código de teletransporte previamente adaptado conserva su atribución en el mod.
- [Devil Mine Craft](https://www.curseforge.com/minecraft/mc-mods/devil-mine-craft) describe una combinación de coreografía de cámara, animación, estelas y sonido para sus remates; su licencia figura como All Rights Reserved. Solo se consultó la descripción pública, sin incorporar recursos.
- [Better Combat Particle](https://github.com/MalfuXT/malfu-mods-bc_slash_particle-1.20.1) aporta los cuadros de anillo ya incorporados y atribuidos bajo MIT; se mantiene sin depender de Darkest Hours.

## Aplicación y límites

El experimento actual encuadra a atacante y objetivo desde un lateral relativo al eje entre ambos, en lugar de una órbita completa que podía tapar al jugador detrás del enemigo. El remate corto de Z usa su propia duración, en vez de reproducir únicamente el principio de una toma de 200 ticks. Se mantienen la interpolación, el raycast contra paredes y los disparadores de impacto decididos por el servidor. El foco inicial ya no dispara un pulso de impacto falso.

Esto no es una validación estética ni demuestra compatibilidad con Epic Fight o Devil Mine Craft. Hay que revisar las capturas reales, sobre todo durante los teletransportes y con enemigos grandes, obstáculos, ambas manos, primera persona y la cámara restaurada; después hace falta un playtest del usuario. La pose de guardia y las animaciones de Z/X/C continúan en revisión.

## Ensayo de encuadre Z en primera persona

En la ejecución de cliente `45437063552` se bajó el encuadre del modelo completo (sin alterar los hombros individualmente) y se compararon las fases de la mano derecha e izquierda. La construcción `45437063533` y el fixture terminaron correctamente. Las imágenes 38–41 muestran un encuadre derecho más bajo; en 42–45 los brazos zurdos todavía pueden verse separados o solapados. Este ensayo **no corrige ni valida** el gesto zurdo: requiere cambiar la pose/rotación o el encuadre y volver a comprobar todos los fotogramas. Las capturas C de impactos confirmados también siguen pendientes de revisión artística; un evento de daño no garantiza que la pose coincida visualmente con el golpe. No distribuir el JAR anterior como versión corregida.

El ensayo de simetría `fc9a826` (`45440590468`) desplazó los brazos y la katana zurdos fuera de la pantalla pese a que el fixture y la compilación pasaron. Se revirtió en `f2abb85` y el fixture `45443052143` regeneró las capturas; el gesto zurdo anterior aún requiere corrección. La simetría de offsets en el espacio del modificador no es suficiente para asegurar un encuadre simétrico de cámara.

## Ensayo de variedad para C

La prueba `a4b729b` alternó el corte de Improved Animations usado por X con Serious Player Animations en los impactos 2, 5 y 8, sin cambiar el daño servidor. El cliente real `45469275194` pasó los diez impactos, pero en las capturas posteriores al daño la espada aparece demasiado alta y alejada de la víctima, como una guardia más que un contacto. Se revirtió en `82f345f`; la ejecución `45471640998` regeneró capturas de la versión anterior y volvió a pasar. Este experimento confirma que cambiar clips y ajustar una estimación de contacto no basta: se necesita un retarget o una nueva temporización revisada visualmente. C sigue siendo repetitiva y sin aprobar.

El intento `9f0bd3e` anuló en primera persona la traslación del brazo de espada importada por el gesto de Z. Aunque fixture `45476442271` y compilación pasaron, las capturas mostraron más solapamiento entre los brazos y el zurdo seguía flotando. Se descartó en `270e61f`; el fixture `45478718113` regeneró las capturas previas y pasó junto con la compilación `45478718439`. No debe tratarse la eliminación de esa traslación por sí sola como solución del agarre o del encuadre.

## Alternancia y muestreo temporal

El ensayo `f336ea9` alterna dos cortes de Serious Player Animations, con Better Combat conservando el combate normal. El fixture `45484388992` y la compilación `45484388852` pasaron, pero los fotogramas de daño muestran la hoja del corte alterno hacia el lado opuesto al objetivo. Podría ser recuperación, no necesariamente contacto: es imprescindible inspeccionar todas las fases antes de considerar la pose válida. El muestreo aislado inicial `45486659793` fue tapado por el objetivo del fixture. Se ajustó el fixture para retirar solamente mobs de prueba después de verificar el combate; `45489016857` completó las pruebas de render, pero falló al guardar imágenes, por lo que hay que regenerarlas y revisarlas. Z zurdo y la aceptación completa siguen pendientes; el cambio de C es experimental.

Las fases despejadas del corte lateral (`45491426698`) revelaron que el clip alterno `sword_attack` separaba la katana de la mano; se revirtió en `90dd4fd`. Las nuevas capturas de la versión previa (`45493568612`, imágenes 114–118) muestran que `sword_attack2` también tiene separación de agarre. Un intento de neutralizar solo la traslación de la muñeca (`f56b785`, fixture `45495981143`) no lo solucionó y se revirtió en `4211550`. `45498027170` y la compilación `45498026953` pasaron tras restaurar el código anterior, que sigue con el defecto visible. Hay que corregir el retarget/transformación de mano antes de aprobar o entregar el JAR.

## Ensayo posterior: compensación por fases

El ajuste fijo del ítem a Y=15 (`dcb5541`, visual `45536152917`) acercó la empuñadura durante el contacto, pero la separó claramente durante la anticipación. Se probó interpolación por fases en `0e00ad0`: Y=3 hasta 0,25 s, Y=15 en 0,375–0,5625 s y retorno a Y=3. El ensayo continúa como `stain_c_grip_trial`, derivado de Serious Player Animations y regenerable con `tools/adaptar_agarre_c.py`; se aplica solo a ciertos cortes laterales C. Visual `45539185719` y build `45539185668` pasaron; se añadieron fases locales diestras y zurdas. Algunas vistas acercan el mango, pero una captura aislada no prueba agarre tridimensional, continuidad, sincronización con el servidor ni aprobación del usuario. Esta modificación no está en el JAR 0.21.0-test.

## Ensayo posterior: variedad lateral de C con clips fuera de Better Combat

Investigación de mods antiguos/poco conocidos con licencias reutilizables:

- **Kelvin's Better Player Animations** (`mrzenc/kelvins-better-anims`, MIT,
  Kevin Merrill 2023, autor original inactivo, Fabric 1.19.2): dos cortes de
  espada en JSON estilo PlayerAnimator (`sword_swing_first` 0.36 s,
  `sword_swing_second` 0.4 s), con piernas y torso. Bones heredados en
  snake_case; el adaptador `tools/adaptar_kelvin.py` los renombra a
  camelCase, comprime tiempos a 0.9 s (factor 2.5/2.25) para acercar el
  contacto al mismo tick que los cortes de Serious Player Animations, y
  añade el hueso `rightItem` con la compensación de empuñadura por fases.
  Fuentes fijadas al commit `b03e0e1049a307fcaf8e7a20732e88911a1ba1c6`;
  licencia en `META-INF/KELVIN_BETTER_PLAYER_ANIMATIONS_LICENSE.txt`.
- **Custom Player Animations** (`cpa`, CC-BY-NC-SA-4.0): **no incorporado**
  por la cláusula NC; permitiría capacidad pero no la seguridad de uso que
  exige el proyecto.
- **Locomotion** (Trainguy9512): All Rights Reserved; no incorporado.
- **Mo' Bends** (MIT): animaciones codificadas en Java, no exportables como
  clips JSON; sin incorporación directa.
- **Kelvin's Better Player Animations** también tiene golpes Sneak; no se
  probaron por alcance. Quedan documentados como candidatos futuros.

Cambios aplicados en esta iteración (sin aprobar visualmente):

1. Corrección del límite de ids de animación: el décimo golpe de C (id 16)
   nunca se reproducía en clientes por una tabla de 16 entradas (0–15).
2. Rotación determinista de cortes laterales de C:
   `stain_c_grip_trial` → `stain_c_grip_trial2` → `kelvin_swing_first` →
   `kelvin_swing_second`, conservándose `stain_c_overhead` en los golpes
   2, 5 y 8. `stain_c_grip_trial2` deriva de `sword_attack` con las
   ventanas de compensación escaladas a 0.875 (el clip mide 0.875 s).
3. En Z primera persona, la mano libre configurable (`blood_gesture.*`)
   se aplica ahora a la mano no principal (zurdos incluidos).
4. Hipótesis de encuadre para la guardia zurda en tercera persona:
   rotación XP +45 (espejo de la −45 diestra). **Medida y revertida**: la
   vista trasera mostraba la hoja cruzando la espalda; se volvió a 0°.
   El problema de la guardia zurda sigue abierto y no debe arreglarse a
   ciegas.
5. El fixture muestrea los nuevos clips por fases (imágenes 124–139) en
   ambas manos. Son muestras locales; no prueban agarre tridimensional,
   continuidad real, sincronización bajo latencia ni audio. La revisión
   sigue pendiente de playtest humano.
