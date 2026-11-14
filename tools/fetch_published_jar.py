#!/usr/bin/env python3
"""Descarga el JAR PUBLICADO y verifica que es el de verdad.

Por qué existe: el CDN de assets de release
(`release-assets.githubusercontent.com`) y el de artifacts de Actions
(`blob.core.windows.net`) responden 302 a hosts que no son accesibles
desde algunos entornos (redes restringidas, sandbox sin egress). Por eso
la CI deja además el `.jar` en la RAMA DE ARTEFACTOS `artifacts/v<VER>`,
que sí se baja por `codeload.github.com`.

Este script es la vía REPRODUCIBLE de esa descarga:

  1. baja el tarball de la rama de artefactos por codeload;
  2. extrae el `.jar` y su `SHA256SUMS.txt`;
  3. consulta la API de GitHub de la release y compara el SHA-256 y el
     tamaño del ASSET publicado con los del binario descargado;
  4. solo escribe el `.jar` en disco si todo coincide.

Es decir: lo que se entrega es, byte a byte, lo que se publicó.

Uso:
    python3 tools/fetch_published_jar.py [VER] [--out RUTA] [--keep-sums]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import sys
import tarfile
import urllib.request

REPO = "Santi-PdR/modelos"
CODELOAD = "https://codeload.github.com/{repo}/tar.gz/refs/heads/{branch}"
API = "https://api.github.com/repos/{repo}/releases/tags/{tag}"


def _request(url: str, accept: str = "application/vnd.github+json"):
    headers = {"User-Agent": "capatest-fetch/1.0", "Accept": accept}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                  timeout=300)


def download_jar(ver: str) -> tuple[bytes, str]:
    """Devuelve (bytes del jar, contenido de SHA256SUMS.txt)."""
    branch = f"artifacts/v{ver}"
    url = CODELOAD.format(repo=REPO, branch=branch)
    print(f"1) bajando la rama de artefactos: {url}")
    raw = _request(url, accept="application/octet-stream").read()
    print(f"   tarball: {len(raw)} bytes")

    jar_bytes = None
    sums = ""
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            base = member.name.rsplit("/", 1)[-1]
            if base == f"capatest-{ver}.jar" and jar_bytes is None:
                jar_bytes = tf.extractfile(member).read()
            elif base == "SHA256SUMS.txt" and not sums:
                sums = tf.extractfile(member).read().decode("utf-8").strip()
    if jar_bytes is None:
        sys.exit(f"FALLO: la rama {branch} no contiene capatest-{ver}.jar")
    return jar_bytes, sums


def published_digest(ver: str) -> tuple[str, int, str]:
    """Digest, tamaño y nombre del asset .jar publicado en la Release."""
    rel = json.loads(_request(API.format(repo=REPO, tag=f"v{ver}")).read())
    for asset in rel.get("assets", []):
        if asset["name"] == f"capatest-{ver}.jar":
            digest = (asset.get("digest") or "").split(":")[-1]
            return digest, asset["size"], asset["state"]
    sys.exit(f"FALLO: la release v{ver} no tiene el asset capatest-{ver}.jar")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("version", nargs="?", default=None,
                    help="versión del mod (por defecto, la de gradle.properties)")
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="ruta del .jar a escribir (por defecto build/libs/)")
    ap.add_argument("--keep-sums", action="store_true",
                    help="escribe también el SHA256SUMS.txt junto al .jar")
    args = ap.parse_args()

    ver = args.version
    if not ver:
        for line in (pathlib.Path(__file__).resolve().parents[1]
                     / "gradle.properties").read_text().splitlines():
            if line.startswith("mod_version="):
                ver = line.split("=", 1)[1].strip()
                break
    if not ver:
        sys.exit("FALLO: no se pudo deducir la versión")

    jar_bytes, sums = download_jar(ver)
    sha = hashlib.sha256(jar_bytes).hexdigest()
    print(f"2) jar descargado: {len(jar_bytes)} bytes")
    print(f"   sha256: {sha}")
    if sums:
        print(f"   SHA256SUMS.txt de la rama: {sums}")

    api_sha, api_size, state = published_digest(ver)
    print(f"3) asset publicado: {api_size} bytes, estado '{state}'")
    print(f"   digest de la API: {api_sha}")
    if api_sha and api_sha != sha:
        sys.exit("FALLO: el binario descargado NO es el publicado")
    if api_size and api_size != len(jar_bytes):
        sys.exit("FALLO: el tamaño no coincide con el asset publicado")
    if sums and sha not in sums:
        sys.exit("FALLO: el SHA256SUMS.txt de la rama no coincide")
    print("   VERIFICADO: el binario es byte a byte el publicado")

    out = args.out or (pathlib.Path(__file__).resolve().parents[1]
                       / "build" / "libs" / f"capatest-{ver}.jar")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(jar_bytes)
    print(f"4) escrito: {out}")
    if args.keep_sums:
        sums_path = out.parent / "SHA256SUMS.txt"
        sums_path.write_text(sums + "\n")
        print(f"   escrito: {sums_path}")


if __name__ == "__main__":
    main()
