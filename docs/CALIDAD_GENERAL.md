# Revisión transversal del mod

Este apunte recoge una pasada de calidad del mod principal; no constituye una versión ni una certificación de compatibilidad universal.

## 1. Apariencia, animación y luz

El comportamiento visual existente de la capa conserva su separación entre paño, tinte y halo. La adaptación del halo se contrasta con `CapeNocturneTest`, `CapeWornLightTest` y `tools/verify_v1670.py`; los recursos y las comparaciones registradas también pasan `tools/audit_model.py --check`. En esta pasada añadí una protección para que entradas de luz o reloj no finitas no conviertan el pase en un resplandor inválido.

La previsualización geométrica del Brazalete Ascua sigue siendo un estudio independiente en `docs/prototypes/brazalete_ascua/`; no se usa para certificar el render del manto.

## 2. Compatibilidad y equipo

Curios sigue siendo opcional: se resuelve por reflexión, y la API permanece en el paquete de compatibilidad. `CapeFxSmoke` comprueba prioridad pecho/espalda y el slot funcional/cosmético visible, oculto o reemplazado; amplié la matriz para asegurar que una pechera corriente o unos élitros no oculten la capa en `back`. Esa aserción prueba selección de equipo, no el encastre visual F5. Añadí al smoke una escena de captura con set de hierro completo y la capa en `Curios:back` (`armadura-pecho-curios.png`); todavía hay que ejecutar Forge y revisar esa imagen antes de afirmar que no hay solapes. Las combinaciones con proveedores de slots o poses de terceros no se dan por cubiertas.

## 3. Estabilidad y coste

`CapeNocturne` ahora trata luz no finita como día (cero aporte del halo), reutiliza el último tiempo válido ante un reloj de render inválido, neutraliza componentes no finitos del impulso y satura los impulsos extremos sin salir del presupuesto de luz. Añadí regresiones para NaN, infinito y overflow, más un barrido de 729 combinaciones de exposición, tiempo e impulso. El camino normal mantiene la misma curva; no crea partículas ni cambia la cadencia ni el límite de chispas. La protección añade sólo comprobaciones escalares de finitud.

Las pruebas Java correspondientes están incluidas en `CapeNocturneTest`, pero no se pudieron compilar/ejecutar localmente: el entorno no dispone de `javac` ni `gradlew` (el JRE temporal disponible no incluye el compilador). La verificación Python del modelo requiere NumPy y Pillow; se instalaron en un destino temporal y ambos comandos terminaron correctamente:

```text
python3 tools/audit_model.py --check
OPENBLAS_NUM_THREADS=1 python3 tools/verify_v1670.py
```

## 4. Documentación y entrega

La versión pública **v1.67.13** no se modificó. **v1.67.42** sigue siendo la última build de prueba descrita como verificada para `test-1`; este pase no produce JAR, instalador ni Release. El workflow principal mantiene pruebas de Forge optativas y evidencia visual; deben volver a ejecutarse en CI después de integrar cualquier cambio de runtime.

Los runs `45066965803`, `45070016707` y `45071022439` compilaron el JAR de forma reproducible y validaron el empaquetado; cada uno adjuntó el JAR de prueba y capturas Forge. El paso 36 aparecía como fallido, pero hacía un `cmp` silencioso del JAR compilado antes de invocar `verify_forge_postures.py`. Los SHA-256 difieren: build `798d650f…` frente al JAR fijado `4dadd92b…`. Esos tres runs no ejecutaron el análisis geométrico de posturas y no son evidencia de un fallo de malla. No actualizo el JAR fijado automáticamente ni lo presento como versión pública: el código fuente cambió después de crear ese artefacto.

En `45070016707`, el verificador de saltos midió contacto nuevo paño/pierna de `0.6601708378722226u` en pecho; `45071022439` pasó ese paso, `45072590511` midió `0.11810985415833564u`, `45075655245` localizó `0.09830050694031822u` en el tick 56 (pierna derecha, `v17_ribbon_7_seg3`, cubo 5) y `45076847054` midió `0.5473030639126684u` en ese mismo tick (pierna derecha, `v17_ribbon_7_seg4`, cubo 3). El tick 56 cae dentro del inicio de carrera: el probe activa sprint en t=54, aunque el intervalo de captura del salto quieto llegaba hasta t=56. Ajusté ese intervalo para conservar el vuelo validado y su recuperación, sin mezclar el arranque de carrera; no cambia el umbral `<0.05u` y aún requiere repetición en Forge. En `45066965803` reconstruí y validé el JPEG de saltos desde cinco anotaciones Base64 (11.520 bytes, 266×335); sirve como registro visual, no como prueba de los criterios geométricos. Las descargas de logs y de artefactos siguen terminando en `EOF`.

El run `45076847054` ejecutó `verify_forge_postures.py` y el chequeo de hombreras, nado y compatibilidad; las posturas pasaron. El paso de saltos y `Check pinned test JAR identity` fallaron con sus diagnósticos visibles; la CI completa no está verde. El run intermedio `45072034983` había puesto la comparación del JAR antes de Forge y por eso omitió las pruebas; ahora está al final, tras las capturas, y no bloquea los verificadores. El recorte del intervalo del salto quieto descrito arriba aún no se ha ejecutado en Forge. No se rebajan umbrales ni se reemplaza el JAR de prueba.

Siguen pendientes las combinaciones F5 con armadura completa y algunas capas/poses aportadas por otros mods. No se extiende una prueba de Forge a casos que no observó.
