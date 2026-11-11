# Prompt para entregar a Claude — rehacer la SKIN de la capa

> Este mismo texto está dentro del ZIP como `PROMPT.md` y, en versión plana
> para copiar/pegar, como `PROMPT.txt`.
> **El icono está aprobado: no se toca.** El problema es sólo la skin de la
> capa equipada.

---

## TEXTO PARA COPIAR Y PEGAR

```
Estás trabajando en el proyecto de este ZIP (la carpeta `proyecto/` es un repo
de Git sin el `.git`, rama `arena/1ea42902-modelos`, estado HEAD `c3c7803`).

CONTEXTO
Mod de Minecraft Java: Forge 1.20.1 / 47.3.0, Java 17, Gradle 8.8,
GeckoLib 4.8.x, Curios 5.14.1+1.20.1. El item es una capa equipada en el slot
`curios:back` (mantle / "Mantle of the Blight Star"). La temática pedida es
"Deterioro (Shigaraki) + Evil Saiyan Rosé": una prenda podrida y
desintegrándose, con energía rosa-magenta.

TAREA
Rehacer LA SKIN / TEXTURA de la capa equipada —y su geometría si hace falta
para que se lea bien— para que se parezca a la referencia
`referencias/01_OBJETIVO_blockbench.png` (y al recorte ampliado
`referencias/01b_OBJETIVO_detalle.png`). El usuario rechazó DOS intentos
anteriores diciendo "la skin de la capa la haces muy mal": mirá
`referencias/02_RECHAZADO_v1140_visor.png` y
`referencias/03_RECHAZADO_v1150_6vistas.png`
para NO repetirlos. Leé también `ESTADO_TECNICO.md` y `referencias/README.md`.

⚠️ EL ICONO ESTÁ APROBADO Y NO SE TOCA
`src/main/resources/assets/capatest/textures/item/capa_deteriorer_evilsaiyan.png`
(64×64 pixel art, SHA-256
e88ccec0a0c67b1ad0982ed781f0d684ae4662660c545fa134574781967e4840) debe quedar
BYTE-IDÉNTICO. Ojo: `tools/texture_pipeline.py` REGENERA el icono cuando lo
ejecutás. Preservá `ICON_PIXEL_MAP`, `ICON_PALETTE`, `ICON_CANDIDATES` e
`ICON_ALTERNATIVE` sin cambios, o restaurá el PNG desde
`referencias/05_ICONO_APROBADO.png`. Al terminar verificá el SHA-256. No
cambies la forma ni la paleta del icono "porque combine mejor": está aprobado
tal cual.

CÓMO DEBE VERSE (mirá la imagen; no la reemplaces por tu interpretación)
- Bufanda / cuello GRUESO carmesí oscuro que envuelve cuello y hombros, con
  el borde inferior RASGADO e irregular. No es un anillo de cajas ni una
  corona de bloques rectangulares.
- De ahí bajan JIRONES ANCHOS con volumen y solape real, que se estrechan en
  puntas desiguales. Silueta ancha arriba, que se deshace abajo; no un
  rectángulo.
- Degradado de color: rojo/carmesí oscuro arriba → violeta / morado desvaído
  en el centro → casi negro abajo, con gris ceniza, suciedad y AGUJEROS
  NEGROS REALES en la tela.
- Energía rosa/magenta en TRAZOS CORTOS Y DISCONTINUOS (grietas encendidas),
  NO en líneas continuas, NO en una red que cubra toda la capa. Ocupa una
  fracción pequeña de la superficie y se concentra en algunas venas.
- Motas / partículas de 1–2 px flotando, ESCASAS, más densas hacia abajo.
- La cabeza blanca del maniquí en la referencia es SÓLO escala: no es parte
  de la prenda, no la exportes como geometría de la capa.

ERRORES A EVITAR (estaban en los intentos rechazados)
- Rejilla / jaula de tiras finas del mismo ancho, todas verticales.
- Neón magenta por toda la superficie, grietas tipo código de barras, franjas
  regulares que se repiten en cada segmento del collar.
- Cubos planos sin grosor, bloques grises que tapan la tela, puntas todas
  iguales, silueta rectangular, cubo blanco por cabeza.
- "Arreglarlo" agregando MÁS tiras, MÁS brillo o MÁS partículas: el problema
  es la MASA DE TELA, la PALETA y la SILUETA. Menos piezas, más anchas, mejor
  pintadas.

RESTRICCIONES TÉCNICAS (no negociables)
- No cambies IDs ni integración: `capatest`, `capa_deteriorer_evilsaiyan`,
  `curios:back` + `player/back`, `animation.item`, `mods.toml`, lang,
  partículas, `CapaItemGlowLayer`. Cero mixins.
- Atlas de armadura 128×128: el canal ALFA debe quedar prístino (no abras
  transparencias nuevas) y los 1636 texels emisivos del glowmask se
  conservan. Todas las UV ≤ 128 y dentro de `OPAQUE_RECTS` de
  `tools/cloth_spec.py` (`assert_opaque`).
- Geo JSON: raíz sin `parent`, 0 `JsonNull`, 0 `"parent": null`; los 72
  huesos de `tools/originals/capa_deteriorer_evilsaiyan.geo.json` van al
  principio BYTE-IDÉNTICOS; `inflate` entre 0.01 y 0.05; espesor de tela
  0.25–0.50; rotaciones en radianes en Java y fail-safes.
- `.bbmodel`: formato `bedrock` con `meta.format_version: "5.0"` y UNA sola
  textura (`single_texture: true`; si incluís maniquí, 128×144 con el atlas
  en las primeras 128 filas). Los UUID deben ser canónicos
  8-4-4-4-12: Blockbench usa `isUUID()` y con md5 de 32 caracteres los
  animadores quedan HUÉRFANOS. Debe tener animaciones REALES con keyframes
  enganchados a UUID de grupos (NO `animations: []`).
- Si tocás `CapaArmorModel.java`, regenerá `DETERIORO_NAMES` para que
  coincida con los nombres `v16_*` que existan realmente.

CÓMO TRABAJAR (no hay gradle/java en este entorno; el build Java lo hace
GitHub Actions al hacer push)
  python3 -m pip install --target tools/_deps Pillow numpy PyYAML
  export PYTHONPATH=tools/_deps
  python3 tools/armor_model_pipeline.py        # geo equipado
  python3 tools/texture_pipeline.py            # atlas, glowmask, item, ICONO
  python3 tools/bbmodel_export.py              # .bbmodel + animaciones
  python3 tools/preview_cloth.py --out /tmp/preview --uv-test   # renders
  python3 tools/build_standalone_preview.py   # visor HTML autocontenido
El bloque "Validate resources" de `.github/workflows/build.yml` es la lista
canónica de invariantes: ejecutalo (o extraé su heredoc de Python) antes de
dar nada por terminado. `README.md` y `ESTADO_TECNICO.md` documentan el
pipeline, el historial de versiones y los callejones sin salida.

ENTREGABLES
1. `src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json`
2. `src/main/resources/assets/capatest/textures/item/armor/capa_deteriorer_evilsaiyan.png`
   y su `_glowmask.png`
3. `docs/*.bbmodel` con animaciones + `docs/*_visor.html` autocontenido
4. Previews PNG (`tools/preview_cloth.py`, 6 vistas) para revisión visual
5. Un resumen breve de qué cambiaste y por qué, y la verificación del SHA-256
   del icono

REGLA DE PROCESO: NO hagas commit, push, build de Release ni publiques nada
sin que el usuario haya mirado los previews y aprobado VISUALMENTE el
resultado. Ya pasó dos veces que se publicó algo que no se parecía a la
referencia. Primero mostrá el render, esperá aprobación, y recién ahí
compilás.

Empezá por abrir las imágenes de `referencias/` y describir en un párrafo qué
ves, antes de tocar código. Si algo de la referencia no está claro,
preguntalo en vez de inventar.
```

---

## Anexo: qué incluye el ZIP

| Ruta | Contenido |
|---|---|
| `PROMPT.md` / `PROMPT.txt` | Este prompt, completo / plano para pegar |
| `ESTADO_TECNICO.md` | Mapa del repo, invariantes, historial y errores conocidos |
| `referencias/` | Objetivo, rechazados, icono aprobado y capturas in-game |
| `referencias/README.md` | Qué es cada imagen |
| `CHECKSUMS.sha256` | Hash del icono y de los originales prístinos |
| `proyecto/` | Repo completo: `src/`, `tools/`, `docs/`, `preview/`, `.github/`, Gradle, README |

Se excluyeron `.git/`, `tools/_deps/` (97 MB de dependencias Python),
`__pycache__/` y `build/`. Para regenerar lo que falta: ver el bloque
"CÓMO TRABAJAR" del prompt.
