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

El run CI `45066965803` pasó validación de recursos, pruebas Java, compilación, reproducibilidad y comprobación del JAR empaquetado; adjuntó el JAR de prueba y capturas de Forge como artefactos. Falló `Revisar las posturas de Alex y medir los cruces de malla`. El endpoint devolvió 50 anotaciones sin incluir ese diagnóstico. Pude reconstruir y validar el JPEG de saltos desde cinco anotaciones Base64: 11.520 bytes, 266×335; documenta una captura, pero no demuestra por sí sola que pasen los criterios de malla.

En la ejecución `45070016707` fallaron los pasos 27 (saltos) y 36 (posturas). `verify_forge_jumps.py` reportó contacto geométrico nuevo de paño/pierna de `0.6601708378722226u` en pecho. La anotación de error de posturas volvió a faltar entre las 50 expuestas por la API. Las descargas de logs y del artefacto de capturas terminan en `EOF`; no atribuyo una causa visual a la falla de posturas sin esa evidencia.

El workflow actualizado guarda las galerías en `capatest-fx-en-mundo` y reduce avisos de éxito después del chequeo de posturas, para reservar anotaciones a diagnósticos de error. El cambio está en `753b6fc` y requiere otra ejecución; no cambia umbrales ni corrige por sí mismo ninguno de los dos fallos. No se declara exitosa la prueba Forge ni la CI.

Siguen pendientes las combinaciones F5 con armadura completa y algunas capas/poses aportadas por otros mods. No se extiende una prueba de Forge a casos que no observó.
