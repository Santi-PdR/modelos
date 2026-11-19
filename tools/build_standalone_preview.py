#!/usr/bin/env python3
"""Empaqueta el visor offline con GEO, animación, texturas y .bbmodel reales."""
from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path

from bbmodel_export import VER

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "preview"
ASSETS = PREVIEW / "assets"
OUT = ROOT / "docs/capa_v1170_visor.html"  # URL histórica del visor, contenido actual


def data(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> None:
    html = (PREVIEW / "index.html").read_text().replace("Desarrollo local", f"v{VER} · Offline")
    app = (PREVIEW / "app.js").read_text()
    loader = """async function loadJson(name) {
  return {'armor.geo.json': INLINE_GEO, 'armor.animation.json': INLINE_ANIMATIONS, 'fit.json': INLINE_FIT,
          'reference-frame.json': INLINE_REFERENCE, 'aura.json': INLINE_AURA,
          'nocturne.json': INLINE_NOCTURNE, 'stride.json': INLINE_STRIDE, 'sway.json': INLINE_SWAY}[name];
}
function assetUrl(name) { return INLINE_IMAGES[name]; }"""
    app, n = re.subn(r"/\* BEGIN LOCAL LOADER \*/.*?/\* END LOCAL LOADER \*/", loader, app, flags=re.S)
    assert n == 1
    inline = {
        "INLINE_GEO": json.loads((ASSETS / "armor.geo.json").read_text()),
        "INLINE_ANIMATIONS": json.loads((ASSETS / "armor.animation.json").read_text()),
        "INLINE_FIT": json.loads((ASSETS / "fit.json").read_text()),
        "INLINE_STRIDE": json.loads((ASSETS / "stride.json").read_text()),
        "INLINE_SWAY": json.loads((ASSETS / "sway.json").read_text()),
        "INLINE_REFERENCE": json.loads((ASSETS / "reference-frame.json").read_text()),
        "INLINE_AURA": json.loads((ASSETS / "aura.json").read_text()),
        "INLINE_NOCTURNE": json.loads((ASSETS / "nocturne.json").read_text()),
        "INLINE_IMAGES": {name: data(ASSETS / name)
                          for name in ("armor.png", "armor_glowmask.png", "armor_halo.png", "reference-crop.png",
                                       *(f"capa_spark_{i}.png" for i in range(3)))},
    }
    script = "<script>\n" + "".join(f"const {k} = {json.dumps(v, separators=(',', ':'))};\n"
                                     for k, v in inline.items()) + app + "\n</script>"
    html = html.replace('<script src="app.js"></script>', script)

    def asset_ref(m: re.Match) -> str:
        attr, name = m.groups()
        extra = f' download="CAPA_v{VER}.bbmodel"' if name.endswith(".bbmodel") else ""
        return f'{attr}="{data(ASSETS / name)}"{extra}'

    html = re.sub(r'(src|href)="assets/([A-Za-z0-9_.-]+)"', asset_ref, html)
    assert "fetch(" not in html and '"assets/' not in html, "quedan referencias de red"
    OUT.write_text(html)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(html):,} bytes, autocontenido")


if __name__ == "__main__":
    main()
