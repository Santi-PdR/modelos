# Referencia: Ultimate Battle

- Página: https://www.curseforge.com/minecraft/mc-mods/ultimate-battle
- Vídeo de movimientos: https://www.youtube.com/watch?v=he2PYcbVRVI (Blade comienza en 00:00, según sus capítulos). Solo se consultaron los metadatos; no se analizó el vídeo fotograma a fotograma.
- Referencia analizada: Ultimate Battle 1.1.1 para Minecraft 1.20.1, CurseForge 9385647. Es Fabric, no Forge. Licencia declarada en el JAR: All-Rights-Reserved.
- Su página describe un combo básico de cuatro golpes y ultimates con cortes de cámara, inclinación e impactos; también permite desactivar las cinemáticas.
- El análisis estático de bytecode de Blade identifica acciones de servidor separadas para CrescentWave, IaiFlash y ThousandCuts. ThousandCuts contiene llamadas a fijar, desplazar y golpear, con posiciones de desplazamiento calculadas alrededor del objetivo.
- En el cliente, ThousandCuts utiliza una animación de habilidad y una función de cámara con varias poses, interpolación y órbitas. Las firmas y llamadas están resumidas en `ultimate_battle_auditoria.txt`; no se han analizado fotogramas ni demostrado las fases concretas de la ejecución.
- Aplicación propuesta para Stain: sincronizar anticipación, acercamiento, posiciones de ataque e impactos por servidor; dirigir cámaras que enfaticen el ataque sin afectar la puntería; conservar opción para desactivar el encuadre; seguir comprobando obstáculos y cancelaciones. Son ideas de diseño, no una implementación incorporada.
- No redistribuir ni copiar código, animaciones o efectos de Ultimate Battle. Los efectos de Stain deben proceder de otras fuentes autorizadas, como pidió el usuario.
