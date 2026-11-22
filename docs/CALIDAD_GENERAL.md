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

Los runs `45066965803`, `45070016707` y `45071022439` compilaron el JAR de forma reproducible y validaron el empaquetado; cada uno adjuntó el JAR de prueba y capturas Forge. El paso 36 apareció como fallido, pero el workflow hacía un `cmp` silencioso del JAR compilado contra `entregables/v1.67.42/capatest-1.67.42.jar` **antes** de invocar `verify_forge_postures.py`. Los SHA-256 son distintos: build `798d650f…` frente al JAR de prueba fijado `4dadd92b…`. Por tanto, esos runs no llegaron a ejecutar el análisis de posturas y no son evidencia de un fallo geométrico de Alex. No actualizo el JAR fijado automáticamente ni lo presento como versión pública: el código fuente ha cambiado desde ese artefacto.

En el run `45070016707`, el paso de saltos sí falló: el máximo nuevo de contacto geométrico paño/pierna fue `0.6601708378722226u` en pecho. En el run siguiente (`45071022439`) el mismo paso pasó; queda como resultado variable que requiere seguimiento, no como validación estable. En `45066965803` pude reconstruir y validar el JPEG de saltos desde cinco anotaciones Base64 (11.520 bytes, 266×335); documenta capturas, pero no demuestra por sí sola que pasen los criterios de malla. Las descargas de logs y del artefacto terminan en `EOF`.

El workflow separa ahora la comparación del JAR fijado en un paso explícito con ambos hashes, para que no se etiquete como fallo de posturas y el analizador geométrico pueda ejecutarse. También reduce avisos de éxito y deja las galerías en `capatest-fx-en-mundo`, reservando anotaciones para errores. Estas correcciones están en el árbol actual y requieren otra ejecución; todavía no hay una ejecución que confirme el análisis de posturas, ni una CI completa exitosa. No se rebajan umbrales ni se reemplaza el JAR de prueba.

Siguen pendientes las combinaciones F5 con armadura completa y algunas capas/poses aportadas por otros mods. No se extiende una prueba de Forge a casos que no observó.
