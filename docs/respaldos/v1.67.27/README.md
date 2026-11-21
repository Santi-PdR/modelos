# Respaldo de las animaciones de v1.67.27

Copia exacta, anterior a los cambios de transición, reposo, agachado y montaje de v1.67.28. Incluye las curvas equipadas y plegadas y el proyecto editable. `sha256sum -c SHA256SUMS.txt` comprueba las tres copias.

- [JAR exacto y resultados de v1.67.27](../../releases/v1.67.27/notas.md), para volver atrás sin recompilar.
- [Fuentes de v1.67.27](https://github.com/Santi-PdR/modelos/tree/185c952a81b2abc5d1cbae778108d0b141d3d870), con la mezcla de clips, la inercia y el montaje que no se guardan en Blockbench.

Se puede abrir el `.bbmodel` directamente o recuperar las curvas copiando `animations/` al directorio `src/main/resources/assets/capatest/`. Para recuperar el comportamiento completo, usar el JAR anterior o sus fuentes y no sólo los JSON. El respaldo no se empaqueta en el mod.
