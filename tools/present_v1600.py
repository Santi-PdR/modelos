#!/usr/bin/env python3
"""Comparación registrada con el PNG, desde los mismos assets del JAR."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import cape_animation_pipeline as A
import cape_reference as R
import preview_cloth as P
from present_v1590 import BG, DIM, INK, ROSE, label, motion_gif, motion_sheet
from verify_v1600 import crop, registered_metrics

BG_PANEL=(29,24,34)
NEUTRAL_PALETTE=((227,226,232),(40,38,47),(59,54,64),(59,54,64),(45,40,48),(45,40,48))


def pose_view(geo, tex):
    """Un portador neutro, misma cámara y luces para ambos renders."""
    s, frame, box = R.render_frame()
    player=[(o, dim, c) for (o,dim,_),c in zip(P.MANNEQUIN_BOXES,NEUTRAL_PALETTE)]
    return P.render(geo,tex,P.effective_hidden(geo),yaw=R.YAW,pitch=R.PITCH,
                    size=s,frame=frame,bg=BG_PANEL,mannequin=player).crop(box)


def panel(out, stamp, newer, atlas, *, prior='1.60.0'):
    ref = Image.open(R.SOURCE).convert('RGB').crop(R.CROP)
    suffix = stamp.replace('.', '')
    backup = P.ROOT/'docs/respaldos'/f'v{prior}'
    baseline = P.load(backup/P.ARMOR_GEO.relative_to(P.ASSETS))
    old_atlas = backup/P.ARMOR_TEX.relative_to(P.ASSETS)
    (old,new),pink = registered_metrics(baseline,newer,atlas,baseline_atlas=old_atlas)
    notes=Image.new('RGB',(1304,1130),BG)
    d=ImageDraw.Draw(notes)
    label(d,(32,25),'MANTLE OF THE BLIGHT STAR   /   v'+stamp,19,ROSE,bold=True)
    label(d,(30,56),'Capa y referencia, borde a borde',54,bold=True)
    label(d,(34,130),'Una sola cámara y escala para comparar las tres siluetas.',21,DIM)
    size=(396,638)
    views=(('01   IMAGEN ORIGINAL',ref),('02   ANTES · v'+prior,pose_view(baseline,old_atlas)),
           ('03   AHORA · v'+stamp,pose_view(newer,atlas)))
    for i,(subtitle,view) in enumerate(views):
        x=32+i*422
        label(d,(x,188),subtitle,18,ROSE if i==2 else DIM,bold=True)
        notes.paste(view.resize(size,Image.Resampling.NEAREST),(x,220))
        d.rectangle((x,220,x+size[0]-1,220+size[1]-1),outline=(81,56,82))
    measurements=(('CONTORNO',f'{old["all"]:.1%} → {new["all"]:.1%}','Solapamiento de la silueta'),
                  ('CUELLO + HOMBROS',f'{old["upper"]:.1%} → {new["upper"]:.1%}','Silueta de la región alta'),
                  ('COSTURA EN U',f'{old["seam"]:.1%} → {new["seam"]:.1%}','Solapamiento de la costura'),
                  ('COLOR',f'{old["mae"]:.1f} → {new["mae"]:.1f} / 255','Menos error en las mismas zonas'))
    for i,(title,value,body) in enumerate(measurements):
        x=32+i*313
        d.rounded_rectangle((x,888,x+300,1018),radius=10,fill=(35,27,42),outline=(77,55,79))
        label(d,(x+15,903),title,14,ROSE,bold=True)
        label(d,(x+14,929),value,29,INK,bold=True)
        label(d,(x+15,983),body,15,DIM)
    label(d,(33,1045),'IoU = intersección ÷ unión de las siluetas trazadas. El color se mide en sus píxeles comunes.',16,DIM)
    label(d,(33,1077),'Los renders no copian el pelo, la ropa del portador ni las motas del fondo. No son capturas del juego.',16,DIM)
    notes.save(out/f'capa_v{suffix}_antes_despues.png',optimize=True)

    # Mapa de diferencia con el mismo recorte, sin un umbral de color para
    # la predicción. Una máscara oscura no puede esconder errores de forma.
    _, labels, energy = (crop(x) for x in R.reference())
    guide = Image.new('RGB',(968,766),BG)
    d=ImageDraw.Draw(guide)
    label(d,(29,27),'Registro de silueta',34,bold=True)
    label(d,(30,77),'Cuello, costura, hombreras y paño. El pelo y las motas no puntúan.',16,DIM)
    truth=labels>0
    palette=np.asarray([[27,21,34],[123,41,64],[83,62,111],[61,53,76],[179,107,133]])
    drawn=palette[labels].copy();drawn[energy]=(224,82,164)
    for i,(title,mask) in enumerate((('01   TRAZADO ORIGINAL',None),('02   v'+prior,old['match']),('03   v'+stamp,new['match']))):
        x=29+i*315
        label(d,(x,115),title,17,ROSE if i==2 else DIM,bold=True)
        rgb=drawn if mask is None else np.where((truth&mask)[...,None],(132,118,156),
                np.where((mask&~truth)[...,None],(206,85,116),np.where((truth&~mask)[...,None],(97,213,186),(27,21,34))))
        guide.paste(Image.fromarray(rgb.astype(np.uint8)).resize((280,452),Image.Resampling.NEAREST),(x,150))
    label(d,(29,626),'Violeta: intersección  ·  Rosa: sobra geometría  ·  Verde: falta geometría',16,DIM)
    label(d,(29,666),f'Rosa intenso visible sobre zona común: {new["pink"]:.1%} en v{stamp} · {pink:.1%} en la referencia.',16,DIM)
    label(d,(29,694),'La geometría, no la máscara de color, determina el contorno predicho.',16,DIM)
    guide.save(out/f'capa_v{suffix}_registro.png',optimize=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--gif',action='store_true')
    args=p.parse_args();out=args.out
    out.mkdir(exist_ok=True,parents=True)
    geo=P.load(P.ARMOR_GEO);ver=P.mod_version();atlas=P.ARMOR_TEX
    clips=json.loads(A.ANIM.read_text())['animations']
    prior = '1.59.0' if ver == '1.60.0' else '1.60.0'
    panel(out,ver,geo,atlas,prior=prior)
    suffix = ver.replace('.', '')
    shutil.copyfile(out/f'capa_v{suffix}_antes_despues.png',out/'capa_v1170_comparativa.png')
    shutil.copyfile(out/f'capa_v{suffix}_registro.png',out/'capa_v1170_silhouette_compare.png')
    motion_sheet(out/'capa_v1170_estados.png',geo,atlas,clips,ver)
    if args.gif:
        motion_gif(out/'capa_v1170_animaciones.gif',geo,atlas,clips,ver)
    print(f'registro de referencia + ciclos v{ver}')


if __name__=='__main__':
    main()
