#!/usr/bin/env python3
"""Materializa el JAR EXACTO de una version desde un ARTIFACT HISTORICO.

Por que existe: la release `v1.27.0` publico su `.jar` como asset y como
artifact de Actions, pero el CDN de assets (`release-assets.githubusercontent.com`)
y el de artifacts (`blob.core.windows.net`) NO son accesibles desde todos
los entornos (redes restringidas, sandbox sin egress). Para dejar el
binario de la v1.27.0 descargable y verificable por la via que SI funciona
(codeload, rama de artefactos) hace falta rescatarlo de su artifact
historico y publicarlo en `artifacts/v1.27.0` con su `SHA256SUMS.txt`.

Este script hace ese rescate:

  1. baja el ZIP del artifact de Actions por la API del repo;
  2. extrae el `capatest-<VER>.jar` que lleva dentro;
  3. comprueba su SHA-256 contra el digest que la API de la release
     publica para el asset (asi se sabe que es el binario entregado, no
     una recompilacion cualquiera);
  4. escribe el `.jar` y su `SHA256SUMS.txt`.

El paso 3 es el que importa: si el SHA no coincide con el de la release,
el script aborta y no escribe nada.

Uso:
    python3 tools/materialize_artifact_jar.py --artifact 14057282072 \
        --version 1.27.0 [--out build/libs]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import sys
import urllib.request
import zipfile

REPO = "Santi-PdR/modelos"
API_ARTIFACT = "https://api.github.com/repos/{repo}/actions/artifacts/{aid}/zip"
API_RELEASE = "https://api.github.com/repos/{repo}/releases/tags/v{ver}"


def _request(url: str, accept: str = "application/vnd.github+json") -> bytes:
    headers = {"User-Agent": "capatest-materialize/1.0", "Accept": accept}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=600).read()


def release_digest(ver: str) -> tuple[str, int]:
    """(sha256, tamaño) del asset `capatest-<ver>.jar` de la release."""
    rel = json.loads(_request(API_RELEASE.format(repo=REPO, ver=ver)))
    for asset in rel.get("assets", []):
        if asset["name"] == f"capatest-{ver}.jar":
            digest = (asset.get("digest") or "").split(":")[-1]
            return digest, int(asset["size"])
    sys.exit(f"FALLO: la release v{ver} no tiene el asset capatest-{ver}.jar")


def artifact_jar(artifact_id: int, ver: str) -> bytes:
    """Bytes del `capatest-<ver>.jar` dentro del artifact de Actions."""
    url = API_ARTIFACT.format(repo=REPO, aid=artifact_id)
    print(f"1) bajando el artifact {artifact_id}: {url}")
    raw = _request(url, accept="application/vnd.github+json")
    print(f"   zip: {len(raw)} bytes")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        wanted = f"capatest-{ver}.jar"
        hit = next((n for n in names if n.rsplit("/", 1)[-1] == wanted), None)
        if hit is None:
            sys.exit(f"FALLO: el artifact no contiene {wanted}. Contiene: {names}")
        return z.read(hit)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", type=int, required=True,
                    help="ID del artifact historico de Actions")
    ap.add_argument("--version", required=True, help="version del mod (1.27.0)")
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("build/libs"),
                    help="carpeta donde escribir el .jar y el SHA256SUMS.txt")
    args = ap.parse_args()

    jar = artifact_jar(args.artifact, args.version)
    sha = hashlib.sha256(jar).hexdigest()
    print(f"2) jar extraido: {len(jar)} bytes")
    print(f"   sha256: {sha}")

    want_sha, want_size = release_digest(args.version)
    print(f"3) asset publicado v{args.version}: {want_size} bytes, sha {want_sha}")
    if want_size and want_size != len(jar):
        sys.exit("FALLO: el tamano NO coincide con el asset publicado")
    if want_sha and want_sha != sha:
        sys.exit("FALLO: el SHA-256 NO coincide con el asset publicado")
    print("   VERIFICADO: es byte a byte el binario de la release")

    args.out.mkdir(parents=True, exist_ok=True)
    jar_path = args.out / f"capatest-{args.version}.jar"
    sums_path = args.out / "SHA256SUMS.txt"
    jar_path.write_bytes(jar)
    sums_path.write_text(f"{sha}  {jar_path.name}\n")
    print(f"4) escrito: {jar_path}")
    print(f"   escrito: {sums_path}")


if __name__ == "__main__":
    main()
