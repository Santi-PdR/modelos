#!/usr/bin/env python3
"""Materializa el JAR EXACTO de una version publicada, y lo deja verificable.

Por que existe: la release `v1.27.0` publico su `.jar` como asset de
release y como artifact de Actions, pero sus CDN (`release-assets.
githubusercontent.com` y `blob.core.windows.net`) no son accesibles
desde todos los entornos (redes restringidas, sandbox sin egress). Para
dejar ese binario descargable y verificable por la via que SI funciona
(codeload, rama de artefactos) hace falta publicarlo en
`artifacts/v1.27.0` con su `SHA256SUMS.txt`.

Este script lo hace, probando DOS fuentes y exigiendo el MISMO digest en
ambas:

  1. el ASSET de la release (fuente primaria, por la API con
     `Accept: application/octet-stream`);
  2. el ARTIFACT historico de Actions (respaldo, por la API de artifacts).

La comprobacion que manda es el SHA-256: se compara con el digest que
publica la API de la release para el asset `capatest-<VER>.jar`. Si el
binario bajado no coincide byte a byte, el script aborta y no escribe
nada. Un binario reconstruido NO sirve: aunque tenga el mismo contenido,
su digest es otro.

Uso:
    python3 tools/materialize_published_jar.py --version 1.27.0 \
        [--artifact 14057282072] [--out build/libs]
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
API_RELEASE = "https://api.github.com/repos/{repo}/releases/tags/v{ver}"
API_ASSET = "https://api.github.com/repos/{repo}/releases/assets/{aid}"
API_ARTIFACT = "https://api.github.com/repos/{repo}/actions/artifacts/{aid}/zip"


def _token() -> str | None:
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def _headers(accept: str) -> dict[str, str]:
    headers = {"User-Agent": "capatest-materialize/1.0", "Accept": accept}
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(url: str, accept: str = "application/vnd.github+json") -> bytes:
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=_headers(accept)), timeout=900).read()


def release_asset(ver: str) -> tuple[int, str, int]:
    """(asset_id, digest sha256, tamaño) del .jar publicado en la release."""
    rel = json.loads(_get(API_RELEASE.format(repo=REPO, ver=ver)))
    for asset in rel.get("assets", []):
        if asset["name"] == f"capatest-{ver}.jar":
            digest = (asset.get("digest") or "").split(":")[-1]
            return int(asset["id"]), digest, int(asset["size"])
    sys.exit(f"FALLO: la release v{ver} no tiene el asset capatest-{ver}.jar")


def from_release_asset(asset_id: int) -> bytes:
    print(f"   probando el asset de la release (id {asset_id})")
    return _get(API_ASSET.format(repo=REPO, aid=asset_id),
                accept="application/octet-stream")


def from_artifact(artifact_id: int, ver: str) -> bytes:
    print(f"   probando el artifact historico {artifact_id}")
    raw = _get(API_ARTIFACT.format(repo=REPO, aid=artifact_id))
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        wanted = f"capatest-{ver}.jar"
        hit = next((n for n in names if n.rsplit("/", 1)[-1] == wanted), None)
        if hit is None:
            sys.exit(f"FALLO: el artifact no contiene {wanted}. Contiene: {names}")
        return z.read(hit)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="version del mod (1.27.0)")
    ap.add_argument("--artifact", type=int, default=None,
                    help="artifact historico de Actions como fuente de respaldo")
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("build/libs"),
                    help="carpeta donde escribir el .jar y el SHA256SUMS.txt")
    args = ap.parse_args()

    asset_id, want_sha, want_size = release_asset(args.version)
    print(f"1) release v{args.version}: asset {asset_id}, {want_size} bytes")
    print(f"   digest publicado: {want_sha}")
    if not want_sha:
        sys.exit("FALLO: la API no publica el digest del asset; no se puede "
                 "garantizar que el binario es el entregado")

    sources = [("release asset", lambda: from_release_asset(asset_id))]
    if args.artifact is not None:
        sources.append(("artifact historico",
                        lambda: from_artifact(args.artifact, args.version)))

    jar = None
    used = None
    for label, fn in sources:
        try:
            data = fn()
        except Exception as exc:                      # noqa: BLE001
            print(f"   [fallo] {label}: {type(exc).__name__}: {exc}")
            continue
        sha = hashlib.sha256(data).hexdigest()
        print(f"   [{label}] {len(data)} bytes, sha256 {sha}")
        if sha != want_sha:
            print(f"   [descartado] {label}: el SHA no es el publicado")
            continue
        jar, used = data, label
        break

    if jar is None:
        sys.exit("FALLO: ninguna fuente dio el binario con el SHA publicado")

    print(f"2) VERIFICADO con la fuente '{used}': es byte a byte el asset "
          f"de la release")
    args.out.mkdir(parents=True, exist_ok=True)
    jar_path = args.out / f"capatest-{args.version}.jar"
    sums_path = args.out / "SHA256SUMS.txt"
    jar_path.write_bytes(jar)
    sums_path.write_text(f"{want_sha}  {jar_path.name}\n")
    print(f"3) escrito: {jar_path}")
    print(f"   escrito: {sums_path}")


if __name__ == "__main__":
    main()
