"""Same-scale fitting and inventory proofs for the mounted cape."""
from __future__ import annotations

import json

import numpy as np
from PIL import Image, ImageDraw

import cape_animation_pipeline as A
import cape_fit as F
import cape_tracks as T
import preview_cloth as P
from present_v1590 import BG, DIM, INK, ROSE, label

BASE = P.ROOT / 'docs/respaldos/v1.63.0'
OLD_GEO = BASE / P.ARMOR_GEO.relative_to(P.ASSETS)
OLD_TEX = BASE / P.ARMOR_TEX.relative_to(P.ASSETS)
OLD_CLIPS = BASE / A.ANIM.relative_to(P.ASSETS)
OLD_ICON = BASE / P.ICON.relative_to(P.ASSETS)


def mount_panel(out, geo, atlas, clips):
    prev = P.load(OLD_GEO)
    old_clips = json.loads(OLD_CLIPS.read_text())['animations']
    board = Image.new('RGB',(1196,997),BG)
    d = ImageDraw.Draw(board)
    label(d,(31,23),'MANTLE OF THE BLIGHT STAR  /  v1.64.0',18,ROSE,bold=True)
    label(d,(29,52),'Sujeción al torso',49,INK,bold=True)
    label(d,(32,117),'Antes y ahora con la misma cámara, escala y postura del portador.',20,DIM)
    # Use the same vanilla part matrices for both columns; no posing the
    # wearer or changing scale to hide the gap in either release.
    player = [(o,dim,color) for (o,dim,_),color in zip(P.MANNEQUIN_BOXES,
              ((170,143,132),(59,99,102),(66,108,108),(66,108,108),(51,54,74),(51,54,74)),strict=True)]
    cases = (
        ('CENITAL · MIRANDO ABAJO', (0.,-78.,0.), (0,83), (0,23,3.8), 'animation.idle', 15.1),
        ('PERFIL · DE PIE', (0.,0.,0.), (-89,10), (0,15.6,3.2), 'animation.idle', 10.3),
        ('PERFIL · AGACHADO', (1.,8.,15.), (-89,13), (0,13.7,5.2), 'animation.sneak', 10.3),
    )
    for i,(name,aim,(yaw,pitch),center,key,scale) in enumerate(cases):
        x = 29+i*387
        label(d,(x,164),name,17,ROSE,bold=True)
        v = (P.R('x',pitch)@P.R('y',yaw)) @ np.array([*center,1.])
        frame = (*v[:2],scale)
        pose = F.mannequin_pose(*aim)
        for j,(model,tex,source,caption) in enumerate(((prev,OLD_TEX,old_clips,'ANTES · v1.63.0'),
                                                       (geo,atlas,clips,'AHORA · v1.64.0'))):
            y = 203+j*373
            c = source[key]
            model = F.wearer_pose(P.pose_at(model,T.prepare_clip(c),c['animation_length']*.39),*aim,legacy=j==0)
            im = P.render(model,tex,P.effective_hidden(model),yaw=yaw,pitch=pitch,size=364,
                          frame=frame,mannequin=player,mannequin_pose=pose,bg=(33,28,40))
            board.paste(im.crop((0,18,364,346)),(x,y))
            d.rectangle((x,y,x+363,y+327),outline=(80,57,87))
            label(d,(x+11,y+11),caption,15,ROSE if j else DIM,bold=True)
    label(d,(30,925),'Montura interior entre el peto y el cuello; las capas de la tela conservan su caída.',18,INK)
    label(d,(30,960),'Render de prueba con pivotes vanilla · no es una captura de Minecraft.',16,DIM)
    board.save(out/'capa_v1640_ajuste.png',optimize=True)


def icon_panel(path):
    board = Image.new('RGB',(906,444),BG)
    d = ImageDraw.Draw(board)
    label(d,(26,20),'INVENTARIO / v1.64.0',16,ROSE,bold=True)
    label(d,(26,51),'Un icono pensado para la ranura',35,bold=True)
    for i,(name,src) in enumerate((('ANTES · v1.63.0',OLD_ICON),('AHORA · v1.64.0',P.ICON))):
        x = 28+i*448
        label(d,(x,113),name,17,ROSE if i else DIM,bold=True)
        icon = Image.open(src).convert('RGBA').resize((16,16),Image.Resampling.NEAREST)
        for j,stage in enumerate(((138,138,138),(58,47,67))):
            y = 145+j*121
            d.rounded_rectangle((x,y,x+395,y+105),8,fill=stage,outline=(102,80,110))
            for scale,slot_x in ((1,30),(3,117),(5,248)):
                im = icon.resize((16*scale,16*scale),Image.Resampling.NEAREST)
                board.paste(im,(x+slot_x,y+(106-im.height)//2),im)
        for dx,mag in zip((30,117,248),('1×','3×','5×'),strict=True):
            label(d,(x+dx,376),mag,14,DIM)
    label(d,(28,413),'✦ La noche arde en sus costuras.',18,ROSE)
    board.save(path,optimize=True)
