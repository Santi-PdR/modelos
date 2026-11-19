"""Same stride, camera and lighting; only the CPU-side cloth hinges differ."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

import cape_fit as F
import cape_stride as S
import cape_tracks as T
import preview_cloth as P
from present_v1590 import BG, DIM, INK, ROSE, label


PLAYER = [(np.asarray(o) + [(.1 if i==4 else -.1) if i>=4 else 0,0,0], s, color)
          for i,((o,s,_),color) in enumerate(zip(P.MANNEQUIN_BOXES,
              ((169,144,132),(59,94,103),(75,119,126),(75,119,126),(68,110,124),(68,110,124)),strict=True))]


def stride_panel(out, geo, atlas, clips):
    board = Image.new('RGB',(1240,1055),BG)
    d = ImageDraw.Draw(board)
    label(d,(30,23),'MANTLE OF THE BLIGHT STAR   /   v1.66.0',17,ROSE,bold=True)
    label(d,(28,57),'El paño cede al paso',46,INK,bold=True)
    label(d,(30,118),'Misma zancada, cámara y escala. El cuello y la montura no se mueven.',20,DIM)
    for row,(name,amp,phase,swing,yaw,title) in enumerate((
            ('moving',.60,.84,.50,-50,'01   /   CAMINAR · PASO LARGO'),
            ('sprint',.85,.64,.50,40,'02   /   ESPRINTAR · BRAZO HACIA ATRÁS'))):
        top=154+row*410
        label(d,(30,top),title,17,ROSE,bold=True)
        clip=clips['animation.'+name]
        aim=(0.,0.,0.)
        arms,legs=S.gait(swing,amp)
        pose=F.mannequin_pose(*aim,arms,legs)
        g=P.pose_at(geo,T.prepare_clip(clip),phase*clip['animation_length'])
        after=S.adjust(g,*S.demand(aim[0],arms,legs),aim)
        for col,(model,caption) in enumerate(((g,'v1.65.0 · SIN HOLGURA DE ZANCADA'),
                                               (after,'v1.66.0 · HOLGURA DEL PAÑO'))):
            x,y=30+col*599,top+33
            staging=(31,25,38)
            model=F.wearer_pose(model,*aim)
            center=(P.R('x',10)@P.R('y',yaw)@np.array([0.,15.5,5.,1.]))[:2]
            image=P.render(model,atlas,P.effective_hidden(model),yaw=yaw,pitch=10,size=581,
                           frame=(*center,9.8),bg=staging,mannequin=PLAYER,mannequin_pose=pose)
            board.paste(image.crop((0,86,581,453)),(x,y))
            d.rectangle((x,y,x+580,y+366),outline=(78,53,82))
            label(d,(x+14,y+11),caption,15,ROSE if col else DIM,bold=True)
    label(d,(30,991),'Sólo giran las dos bisagras del paño; no se desplaza, acorta ni repinta el modelo.',18,INK)
    label(d,(30,1023),'Poses de diagnóstico con maniquí, sin equipo. No son capturas de Minecraft.',16,DIM)
    board.save(out/'capa_v1660_zancada.png',optimize=True)
