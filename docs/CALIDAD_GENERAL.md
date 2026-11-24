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

En `45070016707`, el verificador de saltos midió contacto nuevo paño/pierna de `0.6601708378722226u` en pecho; `45071022439` pasó ese paso, `45072590511` midió `0.11810985415833564u`, `45075655245` localizó `0.09830050694031822u` en t=56 (pierna derecha, `v17_ribbon_7_seg3`, cubo 5) y `45076847054` midió `0.5473030639126684u` en el mismo t=56 (pierna derecha, `v17_ribbon_7_seg4`, cubo 3). Ese sample pertenecía al inicio de carrera: el probe activa sprint en t=54 aunque el intervalo del salto quieto llegaba a t=56. Limité la captura del salto quieto a t=50, que cubre el máximo vuelo permitido y siete ticks de recuperación sin incluir la carrera. En `45077936856` el verificador de saltos pasó sin cambiar el umbral `<0.05u`; es una validación de esa ejecución, no una garantía general de compatibilidad. En `45066965803` reconstruí y validé el JPEG de saltos desde cinco anotaciones Base64 (11.520 bytes, 266×335); sirve como registro visual, no como prueba de los criterios geométricos. Las descargas de logs y de artefactos siguen terminando en `EOF`.

El run `45077936856` pasó las comprobaciones Forge de saltos, posturas, hombreras, nado y compatibilidad, además de build y reproducibilidad. Su único fallo fue `Check pinned test JAR identity`, que sigue mostrando la diferencia `798d650f…` frente a `4dadd92b…`; por eso la CI no está verde y no se adjuntó un JAR nuevo. El run intermedio `45072034983` había puesto la comparación del JAR antes de Forge y omitía las pruebas; ahora está al final, tras las capturas, y no bloquea los verificadores. El cambio de la ventana de captura se validó en esta ejecución, pero sólo se observó un run posterior al ajuste. No se rebajan umbrales ni se reemplaza el JAR de prueba.

Diagnóstico de identidad actualizado: el run `45324865454`, ya con `actions/setup-java@v5`, configuró JDK 17 y volvió a pasar build, reproducibilidad y los verificadores Forge ejecutados; falló únicamente la comparación del JAR fijado. La anotación CI conserva los dos SHA completos: build `798d650fc11322b23acaf5c2aab7bc1d38e0975ed142c177399bdced3dd137d5`, entregable `4dadd92b47ee1026dbfdf56e63563c8dccbd98cb941d767b7d266930711e982a`. El JAR versionado localmente tiene el tamaño esperado (788.533 bytes) y su hash coincide con `JAR.sha256` y con el SHA de la instalación de `test-1`. `compilacion.txt` atribuye ese JAR al run `45033840606`, cuyo SHA de fuente era `bf5a7ba…`; el commit automático que lo adjuntó (`c5e30bc`) tiene exactamente ese padre y no cambió fuentes de runtime. Comparando desde ese pin hasta `ecae86a`, la única diferencia en fuentes de producción es `src/main/java/com/capatest/client/CapeNocturne.java`: se añadieron guardas ante reloj/luz/impulsos no finitos, saturación de overflow y tratamiento de fases extremas; también se agregaron regresiones en `CapeNocturneTest`. El cambio de `setup-java` y las modificaciones de pruebas/herramientas no son cambios del binario de runtime. Esto localiza el motivo del desfase en que el JAR de prueba fijado precede a ese endurecimiento numérico, no en la actualización de `setup-java`; no implica que el JAR actual se haya probado o deba sustituirse. El artefacto de Actions de `45324865454` no se pudo descargar aquí (el endpoint terminó en `EOF`), así que la atribución se basa en el historial de fuentes, el hash del JAR fijado y la anotación del verificador, no en una comparación byte a byte de los dos JAR. No se reemplaza el artefacto automáticamente.

Siguen pendientes las combinaciones F5 con armadura completa y algunas capas/poses aportadas por otros mods. No se extiende una prueba de Forge a casos que no observó.
