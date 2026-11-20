## Mantle of the Blight Star v1.67.14 — versión de prueba

Para **Minecraft Java 1.20.1 · Forge 47.3.0 · GeckoLib 4.8.1**. Curios 5.14.1 es opcional para la ranura `back`.

El borde inferior del cuello conserva su grosor sobre la hombrera al mirar en diagonal y pasa gradualmente a la postura de perfil. El ajuste sólo afecta al cuello visible del modelo equipado: la montura, las placas, el faldón, el atlas y las animaciones no cambian.

**Verificado en Forge, en pecho y Curios.** A ±60° de giro hacia abajo se conserva el 94–97% del cuello visible de v1.67.13 y aparecen 187–229 píxeles de cuello cerca de la camiseta, frente a cero en el control. Es una medición de proximidad en F5, no de contacto. El recorrido de 0° a +79°, −79° y vuelta pasó con 317 fotogramas por ranura y el brillo alineado con el sólido.

[Prueba original en Forge](https://github.com/Santi-PdR/modelos/actions/runs/44765187375) · [Comparativa F5](https://github.com/Santi-PdR/modelos/blob/fd9d8f5611c39378f891999383575443c6c63375/docs/capa_v16714_giro_forge.png)

| Adjunto | Para qué sirve |
| --- | --- |
| `capatest-1.67.14.jar` | Mod verificado para la instancia de prueba |
| `CAPA_v1.67.14.bbmodel` | Proyecto base editable en Blockbench |
| `capa_v1170_visor.html` | Visor offline con el ajuste equipado |
| `capa_v16714_giro_forge.png` | Comparación y recorrido en F5, pecho y Curios |
| `SHA256SUMS.txt` | SHA-256 de cada archivo adjunto, salvo la propia lista |
| `instalar-test-1.txt` | Instalar el JAR local con verificación y respaldo |

### Instalar en `test-1` sin ZIP

Mientras esté en borrador, sólo una cuenta con acceso al borrador puede descargar sus adjuntos. Descargá **sólo `capatest-1.67.14.jar`** desde **Assets** y seguí el bloque de PowerShell de `instalar-test-1.txt`, con Minecraft cerrado. Usa el archivo local, no un enlace de descarga anónimo. Verifica el JAR antes de reemplazar la capa, respalda las versiones anteriores fuera de `mods` y no reemplaza otros mods.

SHA-256 del JAR: `9a00241265b7824666feb283f88f433553d5e80dc440e8a8ad87c12d4e2189db`.

Para la instalación desde la descarga pública, sigue disponible [v1.67.13](https://github.com/Santi-PdR/modelos/releases/tag/v1.67.13).
