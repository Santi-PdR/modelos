#!/usr/bin/env python3
"""Construye un visor 3D AUTOCONTENIDO: un único .html sin fetch ni servidor.

El sandbox de Arena tiene `allowPublicTraffic=false`, así que una URL cruda
`https://8000-....e2b.app` devuelve 403 MISSING TRAFFIC ACCESS TOKEN si se
abre fuera del *live preview* de la plataforma. Este script incrusta geo,
atlas, iconos, GIFs y el .bbmodel como data URLs para que el visor funcione
abriendo el archivo directamente (doble clic o `present_file`).

Uso:  python3 tools/build_standalone_preview.py
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "preview"
ASSETS = PREVIEW / "assets"
OUT = ROOT / "docs/capa_v1140_visor.html"


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def data(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{b64(path)}"


def main() -> None:
    html = (PREVIEW / "index.html").read_text()
    js = (PREVIEW / "app.js").read_text()

    # --- 1. Geo compactado -------------------------------------------------
    geo = json.loads((ASSETS / "armor.geo.json").read_text())
    geo_js = json.dumps(geo, ensure_ascii=False, separators=(",", ":"))

    # --- 2. Sólo las tres definiciones de icono que lee app.js ------------
    pipe = (ASSETS / "icon_src.txt").read_text()
    parts = []
    for name in ("ICON_ALTERNATIVE", "ICON_PIXEL_MAP", "ICON_PALETTE"):
        m = re.search(rf"^{name} = (\(|{{)([\s\S]*?)(?:^\)\s*$|^\}}\s*$)",
                      pipe, re.M | re.S)
        assert m, name
        parts.append(m.group(0))
    icon_js = "\n\n".join(parts)

    # --- 3. app.js sin fetch ----------------------------------------------
    js = js.replace("const GEO_URL = 'assets/armor.geo.json';",
                    "const GEO_URL = null; // incrustado: INLINE_GEO")
    js = js.replace("const ATLAS_URL = 'assets/armor.png';",
                    "const ATLAS_URL = INLINE_ATLAS;")
    js = js.replace("const geo = await (await fetch(GEO_URL)).json();",
                    "const geo = INLINE_GEO;")
    js = js.replace("const txt = await (await fetch('assets/icon_src.txt')).text();",
                    "const txt = INLINE_ICON_SRC;")
    assert "fetch(" not in js, "queda un fetch en app.js"

    inline = (
        "<script>\n"
        "const INLINE_GEO = " + geo_js + ";\n"
        "const INLINE_ATLAS = " + json.dumps(data(ASSETS / "armor.png")) + ";\n"
        "const INLINE_ICON_SRC = " + json.dumps(icon_js) + ";\n"
        "</script>\n"
        "<script>\n" + js + "\n</script>"
    )
    html = html.replace('<script src="app.js"></script>', inline)

    # --- 4. Imágenes y enlaces a data URLs --------------------------------
    def asset_ref(m: re.Match) -> str:
        attr, name, extra = m.group(1), m.group(2), m.group(3)
        p = ASSETS / name
        assert p.is_file(), name
        if name.endswith(".bbmodel"):
            return (f'{attr}="data:application/octet-stream;base64,{b64(p)}" '
                    f'download="capa_deteriorer_evilsaiyan.bbmodel"{extra}')
        return f'{attr}="{data(p)}"{extra}'

    html = re.sub(r'(src|href)="assets/([A-Za-z0-9_.-]+)"([^>]*)',
                  asset_ref, html)
    assert 'assets/' not in html, "queda una referencia a assets/"

    # --- 5. Aviso de que no requiere red ----------------------------------
    html = html.replace(
        '<span class="badge">SIN COMPILAR · SIN PUBLICAR</span>',
        '<span class="badge">SIN COMPILAR · SIN PUBLICAR</span>\n'
        '    <span class="badge" style="border-color:#6ed8f0;color:#6ed8f0">'
        'OFFLINE · SIN SERVIDOR NI TOKEN</span>', 1)
    html = html.replace("<title>", "<!-- Autocontenido: sin fetch, sin servidor, sin token -->\n<title>", 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(html):,} bytes, "
          f"sin fetch y sin referencias externas")


if __name__ == "__main__":
    main()
