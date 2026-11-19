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
