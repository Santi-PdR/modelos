# Capa Deteriorer Test

Mod mínimo de prueba para **Minecraft Java 1.20.1 / Forge 47.3.0 + GeckoLib 4.8.1**.
Añade una capa (armadura de pecho) animada: *Capa Deteriorer Evil Saiyan*, con geo/animaciones
propias, textura con glowmask y animación `idle` / `moving`.

## Estructura

```
build.gradle                 ForgeGradle 6 (plugin [6.0,6.2)), repositorio Modrinth Maven, fg.deobf(GeckoLib)
gradle.properties            Versiones (MC 1.20.1, Forge 47.3.0, GeckoLib bVtfWE8S), datos del mod
settings.gradle              Plugin management Forge + foojay-resolver-convention
src/main/java/com/capatest/  Registro del item, material de armadura, renderer y controlador de animación
src/main/resources/          mods.toml, pack.mcmeta, lang, modelo/animación JSON, texturas
.github/workflows/build.yml  CI: checkout v4, setup-java v17 temurin, setup-gradle v4 (8.8), upload-artifact v4
```

## Compilar en local

Se necesita JDK 17 y Gradle 8.8 (el zip no incluye `gradlew`):

```bash
gradle build --no-daemon
# salida: build/libs/capatest-1.0.0.jar
```

## GitHub Actions

El workflow corre en `push` y `workflow_dispatch` sobre `ubuntu-latest`, ejecuta
`gradle build --no-daemon` y publica `build/libs/*.jar` (excluyendo `*-sources.jar`)
como artifact descargable.

## Probar en Singleplayer

1. Instalar **Forge 1.20.1 - 47.3.0** (o cualquier 47.x reciente) en el launcher.
2. Descargar **GeckoLib 4.8.1 para Forge 1.20.1** desde Modrinth:
   https://modrinth.com/mod/geckolib/version/bVtfWE8S
   (coordenada Maven usada en el build: `maven.modrinth:8BmcQJ2H:bVtfWE8S`).
3. Poner `geckolib` y el `capatest-1.0.0.jar` compilado en la carpeta `mods/`.
4. Crear un mundo nuevo; la capa aparece en la pestaña de combate del menú creativo
   (`/give @s capatest:capa_deteriorer_evilsaiyan`) y se equipa en el slot de pecho.
