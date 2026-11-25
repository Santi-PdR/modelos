# Investigación de mods y técnicas para la cinemática y los FX (24 nov 2026)

Documento de trabajo para la rama `arena/ce4979c1-modelos`. Resume qué mods se analizaron, con qué licencia, qué se tomó en cuenta y qué no se puede usar. El objetivo es mejorar la cinemática de Z/X/C y los efectos, manteniendo la disciplina de atribución: **no se copia código ni assets sin licencia compatible**, y el repo público tampoco admite incorporar material "porque es un mod personal".

> Nota sobre licencias: las licencias mandan sobre la intención. Un mod personal no exime de copyright, y esta rama se publica en GitHub. Además, el usuario prefirió siempre citar el origen. Los mods sin licencia explícita o con CC-BY-NC / GPL fuerte se excluyen o se usan solo como idea.

## Mods analizados

| Mod | Licencia (verificada) | Qué aporta | Qué se usó / qué no |
|---|---|---|---|
| **Oborokage** (胧影剑录, JoryEdward/oborokage) | **MIT**, © 2026, commit`main` | Ultimates con cámara keyframed en tercera persona (yaw/dist/pitch/lift), letterbox + tinte, viñeta, flashes, tarjetas de título por espada, screen shake, arco de corte ("crescent"), partículas propias (PETAL/SPARK/SHARD/MOTE), saya al cinto. Katanas originales con combos, 见切, 架刀. MC 26.x Fabric | **Técnicas, implementadas por nosotros en Forge 1.20.1**: sacudida de cámara aditiva por golpe, rim flash carmesí en la ejecución decisiva, tarjeta de título ("S E N T E N C E" / "P A R A L Y S I S" + subtítulo), impulso de FOV mayor en el remate, rack de motes pálidos reutilizando nuestros sprites `blood_pulse` (tipo `blood_mote` propio). No se copió ninguna clase: la implementación de esta rama es original |
| **Cinema Scope** (heconis) | **MIT** (ya atribuido en `META-INF/CINEMASCOPE_LICENSE.txt`) | Letterbox animado y curvas de cámara suave | En uso desde hace tiempo (`SceneCurve.ease`, `shot`, `impactEnvelope`) |
| **Better Combat** (Daedelus) | ver `META-INF/BETTER_COMBAT_PARTICLE_LICENSE.txt` (Malfu para frames) y el propio mod | Autoridad de combate ordinario; sonidos de corte (`katana_slash`) | Solo sonidos con alternativa vanilla. **Sus clips predeterminados NO se usan** (regla del proyecto y decisión previa) |
| **Serious Player Animations** (McVader, © 2024) | **MIT** (ver `META-INF/SERIOUS_PLAYER_ANIMATIONS_LICENSE.txt`) | Cortes de espada `sword_attack`/`sword_attack2` | En uso desde 0.22.0-test como cortes laterales de C (`stain_c_grip_trial`, `stain_c_grip_trial2`) |
| **Kelvin's Better Player Animations** (mrzenc/kelvins-better-anims @ b03e0e1) | **MIT**, © 2023 Kevin Merrill (ver `META-INF/KELVIN_BETTER_PLAYER_ANIMATIONS_LICENSE.txt`) | `sword_swing_first/second` y variantes `_sneak` (misma estocada, postura agazapada más profunda) | Desde 0.23.0-test: rotación lateral de C amplía a 6 cortes (`kelvin_swing_first_sneak`, `kelvin_swing_second_sneak`), reescalados a 0.9 s con la compensación de empuñadura `rightItem` |
| **Emotecraft** | CC0 | Emote "Inspect" | En uso para el gesto Z (`inspect`) |
| **player-animation-rework** | MIT (continuidad) | Fallback de animaciones | No incorporado todavía; reservado si hace falta una fuente adicional |
| **SlashBlade / SlashBlade_2** (flammpfeil) | **SIN LICENCIA** (todos los derechos reservados) | El referente katana por excelencia (拔刀剑): iaido, combos, filo | **No se pueden usar sus assets ni código.** Su catálogo confirma que hacen falta: draw desde vaina, arco de corte legible y postura de guardia baja |
| **The-Dark-Dimensions** (WahlJanick) | **SIN LICENCIA** | `katana_parry.json`, `katana_finisher.json`, `katana_dodge_*` en formato PlayerAnimator — justo el formato que consumimos | **No se pueden usar.** Queda anotado como referencia de lo que el género necesita (parry, finisher, esquivas) |
| **Epic Fight** | GPL-3.0 | Hit-stop, posturas de empuñadura, dash attack, cámara teledirigida en habilidades | Conceptos generales únicamente; nada copiado |
| **naruto minecraft (radhepa)** | contenido vario | Wardrobe iaido (Blockbench) | Irrelevante (armadura, no animación) |
| **player-animation-rework / dbplayeranim** | MIT | Cortes y emotes adicionales | Ninguno incorporado aún |

## Qué se implementó en 0.23.0-test (esta iteración)

1. **Clips nuevos (MIT, Kelvin)**: `kelvin_swing_first_sneak` y `kelvin_swing_second_sneak`, reescalados a 0.9 s con la misma ventana de compensación `rightItem`; rotación lateral de C ahora es de 6 cortes. Verificados por parser de PlayerAnimator en CI.
2. **Sacudida de cámara por golpe** (`KatanaScene.applyShake`): aditiva, view-only, potencia 0.45 en cortes normales y 1.0 en la ejecución decisiva; decae en 7 ticks; configurable (`screenShakeDegrees`, 0–4, default 1.1); no toca objetivo ni daño. Inspirada en el `kick` de Oborokage/Cinema Scope.
3. **Rim flash carmesí** en la ejecución decisiva (`FINAL_FLASH`): 6 ticks, dos pasadas suaves, acoplado a los impactos servidores `ULTIMATE_FINAL` (C) y `FINISHER` (Z).
4. **Tarjeta de título** (`TITLE_CARD`): "S E N T E N C E" / "P A R A L Y S I S" con subtítulo "v e r e d i c t o  f i n a l", aparición 6 ticks, permanencia ~40 ticks. Ambos desactivables por config (`/mconfig stainkatana`).
5. **Impulso de FOV mayor en el remate** (×1.8 sobre la envolvente de impacto).
6. **Partículas propias nuevas**: `blood_mote` (reutiliza los 6 frames de `blood_pulse`, tinte pálido #FFF3D6, cámara-facing, deriva ascendente); pobladas en la ejecución decisiva de C y Z. Se respeta la regla del build aislado (ningún `ParticleTypes.` en Java).
7. **C fijo**: la rotación lateral ahora usa 6 cortes; el resto del pipeline (compensación `rightItem`, IDs de animación 7–16) sin cambios.

## Qué sigue pendiente (y por qué)

- **Iaido real (draw + vaina)**: requiere un sistema de vaina en la espalda/cintura (como el `WaistSheaths` de Oborokage) y un clip de desenvainado; no hay fuente con licencia compatible incorporable hoy. Es el mayor salto visual pendiente.
- **Hit-stop**: congelar ticks en el impacto decisivo; riesgo de desincronización cliente/servidor; requiere decisión de diseño (single-player only vs red).
- **Cinemática de cierre de C**: hoy el encuadre de C es la órbita lateral existente + zoom + letterbox + flash + título. "Especial popular" = Epic Fight/Oborokage hacen cámara dirigida por espada; muy ambicioso en Forge 1.20.1 con Better Combat autoritario; fase posterior.
- **Poses de empuñadura por ángulo** (igualar el plano del dorso de la mano al ángulo de la hoja): el motor actual compensa por clips, no por IK; requeriría un solver de muñeca propio.
- **Audio**: sigue sin escucharse; ninguna aprobación.
- Imágenes 124–139 y las nuevas capturas son muestras locales; ninguna equivale a playtest.
