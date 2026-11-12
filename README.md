# Holographic Relic — Forge 1.20.1

Modid **`holorelic`**. Accesorio Curios **Núcleo Holográfico / Holographic Core**:
modelo animado sobre el hombro, estelas translúcidas, estado activo/dormant y brillo
emisivo. Proyecto Java 17, Forge **47.4.8**, Curios **5.14.1+1.20.1**, GeckoLib
**4.8.4**. Versiones y APIs contrastadas: [docs/VERSIONES.md](docs/VERSIONES.md).

## Compilar y ejecutar

Con **JDK 17** y acceso a los repositorios Maven declarados:

```sh
./gradlew build
./gradlew runClient
# Servidor dedicado para probar con dos clientes (aceptar EULA en run/eula.txt):
./gradlew runServer
```

En Windows: `gradlew.bat build` / `gradlew.bat runClient`. El wrapper Gradle 8.8
está incluido. JAR esperado: `build/libs/holo-relic-1.20.1-1.0.0.jar`.
En una instalación normal, colocar el JAR y las versiones Forge de Curios y
GeckoLib indicadas en `mods/`, **tanto en servidor como en clientes**.
Las dependencias no se incrustan en el JAR.

**Estado de validación:** seis tests de recursos pasan y los nueve archivos Java
pasan análisis sintáctico con Tree-sitter. `./gradlew build` se intentó y falló
porque este entorno no tiene Java; además el acceso a Maven está restringido.
No se ha verificado compilación, `runClient`, multijugador ni shaders. No se
entrega un JAR supuestamente compilado.

## Uso

- Pestaña creativa **Herramientas y utilidades** o `/give @s holorelic:holographic_core`.
- Equipar en el slot Curios propio **Reliquia**, de tamaño 1; al equipar activo:
  `activation → idle`. El estado apagado se conserva en NBT del ítem.
- **H** (reasignable en Controles) o **`/relic toggle`**: apagar/encender con
  `deactivation → idle_dormant` / `activation → idle`.
- **`/relic pulse`**: `energy_pulse → idle`; no necesita permisos de operador,
  solo afecta al ejecutor con una reliquia activa equipada.
- Glitch aleatorio únicamente cuando está activo y no hay una acción en curso;
  intervalo de 20–60 s desde el final de la acción anterior.
- Las acciones se bloquean durante animaciones puntuales para no cortarlas;
  los comandos explican si hay que esperar. El keybind simplemente ignora el intento.
- Desequipar oculta inmediatamente: **no se mantiene una copia fantasma para
  reproducir deactivation**. Curios ya no invoca el renderizador en ese momento.
- No hay render local en primera persona. Otros portadores siguen visibles.

Receta (G cristal, A fragmento de amatista, E perla de ender, R redstone):

```text
 G
AEA
 R
```

## Configuración

`config/holorelic-client.toml`, local a cada espectador:

| Clave | Predeterminado | Función |
|---|---|---|
| `shoulder` | `LEFT` | `LEFT` / `RIGHT`: refleja X para el otro hombro |
| `scale` | `1.0` | 0.1–4.0; escala alrededor del origen a los pies |
| `offsetX`, `offsetY`, `offsetZ` | `0`, `0`, `0.08` | Bloques en espacio del cuerpo; Y positivo arriba, Z positivo atrás |
| `lowQuality` | `false` | Oculta `drift_01..08` y anillos finos 5–6, incluidos sus hijos |
| `glowLayer` | `true` | Segunda pasada emisiva; desactivable para rendimiento/shaders |

`<mundo>/serverconfig/holorelic-server.toml`, autoritativo y sincronizado por Forge:
`glitchMinSeconds=20`, `glitchMaxSeconds=60` (1–3600; máximo menor al mínimo se
ajusta al mínimo). La configuración de hombro/calidad es visual, no una propiedad
sincronizada del ítem. Reiniciar mundo/cliente tras editar archivos manualmente.

El transform sigue el torso (inclinado al agacharse), no la cabeza. El offset
trasero inicial deja separación de armadura/capa; no hay simulación de colisión
con capas, élitros, armaduras o cuerpos añadidos por otros mods. Ajustar offsets
si una combinación concreta los atraviesa. Escalar también desplaza el anclaje;
compensar con offsets si se desea mantener fija su posición.

## Emisión, transparencia y shaders

La base usa `entityTranslucentEmissive` a luz máxima, sin sombreado direccional,
y la capa opcional lee el PNG `_glowing` intacto con otra pasada emisiva. No se
usa `AutoGlowingGeoLayer`: en esta versión su implementación busca `_glowmask`,
no el sufijo de tus assets. No se reescribe ninguna textura original.

**Emisión no es bloom ni ilumina bloques**. En vanilla mantiene luminosidad en
oscuridad; los halos reales dependen del postprocesado del shader. Oculus/shaders
pueden reinterpretar o ignorar estos RenderTypes, así que **no hay compatibilidad
comprobada**. Iris no es el cargador nativo de shaders para Forge 1.20.1; probar
Oculus con sus dependencias compatibles, no instalar Iris de Fabric sobre Forge.

Punto de integración opcional: capa emisiva en `client/RelicRenderer.java` y rutas
`holorelic:textures/relic_hologram{,_glowing}.png`, para identificación por un shader
que soporte materiales emisivos personalizados. No se depende de APIs de shaders.
Con bloom probar primero `glowLayer=false`: la base permanece emisiva y se evita
la doble pasada (que también puede intensificar el alfa de partes translúcidas).
El orden de transparencias entre cubos/otros mods puede producir artefactos.

## Estructura y assets

```text
build.gradle, settings.gradle, gradle.properties, gradlew[.bat], gradle/wrapper/
src/main/java/dev/holorelic/
  HoloRelic.java, RelicConfig.java, RelicNetwork.java, RelicServer.java
  client/ClientEvents.java, ClientState.java, RelicVisual.java,
         RelicModel.java, RelicRenderer.java
src/main/resources/
  META-INF/mods.toml, pack.mcmeta
  assets/holorelic/{geo,animations,textures,models/item,lang}/
  data/holorelic/{curios/slots,curios/entities,recipes,advancements/recipes}/
  data/curios/tags/items/relic.json
tests/test_resources.py
```

Los cuatro assets de render se copiaron **byte por byte** desde
`reliquia_holografica_v3.zip`; el `.bbmodel`, preview y herramientas siguen intactos
en ese ZIP de referencia. El ZIP de la capa de prueba no se usa ni modifica.
El único PNG nuevo es el icono de inventario 16×16.

Cada portador tiene caché/controlador propio; servidor decide eventos y los manda
solo a observadores y al propietario, también al empezar a observar. No se
transmiten huesos cada tick. Los eventos caducados no se repiten al empezar a
renderizar un jugador. Los recién llegados pueden ver una acción en curso desde
su inicio: no hay sincronización exacta de fotograma entre clientes.
Hay animación continua, sin render en bind pose: transición inicial de 0 ticks
para evitar que `flash`/`shock_ring` aparezcan por defecto, y 2 ticks en cambios
posteriores. Calidad baja evita enviar esos huesos a los buffers; no elimina
sus curvas del archivo de animación ni modifica el modelo.

## Pruebas

Automáticas, sin dependencias Python externas:

```sh
python3 -m unittest discover -s tests -v
```

Validan integridad SHA-256 de assets contra el ZIP, JSON, animaciones/huesos,
slot/tag Curios, tamaños PNG, paridad lang y wrapper JAR. **No sustituyen compilar**.

Checklist manual **pendiente**:

- [ ] `build`, `runClient` y servidor dedicado sin cargar clases cliente en servidor.
- [ ] Obtener por receta/creativo; equipar solo una reliquia; desequipar oculta.
- [ ] Activación completa sin flash inicial; H y `/relic toggle`; persistencia dormant.
- [ ] `/relic pulse`, glitch 20–60 s, bloqueo durante acciones; no glitch dormant.
- [ ] Tercera persona frontal/trasera, ambos hombros, sneak, caminar, armadura y capa.
- [ ] Contrastar orientación/rotaciones con el preview y `.bbmodel` originales.
- [ ] Primera persona propia sin accesorio; otros jugadores sí visibles.
- [ ] Dos clientes: acciones observables, entrar/salir del rango, reconectar,
      cambiar dimensión, morir/reaparecer y cambiar rápidamente el ítem equipado.
- [ ] Noche/cueva: emisión; comprobar alfa/orden de transparencias y recursos F3+T.
- [ ] Sin shaders y con Oculus+shader compatible: bloom opcional, glow activado y apagado.
- [ ] Calidad baja, escala/offsets y varios portadores: comparar FPS y ausencia de fugas visuales.
