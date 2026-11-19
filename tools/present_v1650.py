"""Same-scale worn proof of the small cowl returns and their live mount."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

import cape_fit as F
import cape_tracks as T
import preview_cloth as P
from present_v1590 import BG, DIM, INK, ROSE, label

BASE = P.ROOT / 'docs/respaldos/v1.64.0'
OLD_GEO = BASE / P.ARMOR_GEO.relative_to(P.ASSETS)
OLD_TEX = BASE / P.ARMOR_TEX.relative_to(P.ASSETS)
STAGE = (33, 27, 40)
# Include skin-layer extents at the head and shoulders, even though the
# mannequin has flat colours rather than a particular Minecraft skin.
PLAYER = [(np.asarray(o)-d, np.asarray(s)+2*d, c)
          for (o,s,_),c,d in zip(P.MANNEQUIN_BOXES,
              ((174,147,131),(61,102,105),(69,113,115),(69,113,115),(52,54,72),(52,54,72)),
              (.5,.24,.25,.25,0.,0.),strict=True)]  # separate coplanar shirt/arm faces


def worn(geo, atlas, yaw, pitch, aim, size, scale, center):
    """Fixed lens for before/after; no zoom based on cape visibility."""
    model = F.wearer_pose(geo,*aim)
    xy = (P.R('x',pitch) @ P.R('y',yaw) @ np.array([*center,1.]))[:2]
    return P.render(model,atlas,P.effective_hidden(model),yaw=yaw,pitch=pitch,size=size,
                    frame=(*xy,scale),bg=STAGE,mannequin=PLAYER,
                    mannequin_pose=F.mannequin_pose(*aim))


def collar_panel(out, geo, atlas, clips):
    board = Image.new('RGB',(1280,966),BG)
    draw = ImageDraw.Draw(board)
    label(draw,(30,22),'MANTLE OF THE BLIGHT STAR   /   v1.65.0',17,ROSE,bold=True)
    label(draw,(28,51),'Un poco de cuello, nada sobre el pecho',43,INK,bold=True)
    label(draw,(31,110),'Vista frontal equipada · misma cámara, luz, escala y postura.',20,DIM)

    def panel(im,x,y,w,h,subtitle,active=True):
        cut = (im.width-h)//2
        board.paste(im.crop((0,cut,w,cut+h)),(x,y))
        draw.rectangle((x,y,x+w-1,y+h-1),outline=(86,63,94))
        label(draw,(x+14,y+13),subtitle,15,ROSE if active else DIM,bold=True)

    old = P.load(OLD_GEO)
    for i,(model,tex,caption) in enumerate(((old,OLD_TEX,'ANTES  /  v1.64.0'),
                                           (geo,atlas,'AHORA  /  v1.65.0'))):
        panel(worn(model,tex,180,7,(0,0,0),601,25.3,(0,26.5,1.9)),
              30+619*i,151,601,305,caption,i==1)
    label(draw,(31,486),'El borde acompaña al cuello cuando gira el portador',27,INK,bold=True)
    cases = (
        ('GIRADO  /  TRES CUARTOS', (0.,-12.,26.), (146,9), (0,25.6,2.3), 'animation.moving'),
        ('LADO OPUESTO  /  TRES CUARTOS', (0.,9.,-24.), (-145,9), (0,25.7,2.3), 'animation.idle'),
        ('AGACHADO  /  PERFIL', (1.,-9.,21.), (-89,11), (0,19.8,5.0), 'animation.sneak'),
    )
    for i,(caption,aim,(yaw,pitch),center,key) in enumerate(cases):
        clip = clips[key]
        model = P.pose_at(geo,T.prepare_clip(clip),clip['animation_length']*.39)
        panel(worn(model,atlas,yaw,pitch,aim,394,15.8,center),30+413*i,534,394,324,caption)
    label(draw,(31,884),'Dos remates cortos unidos al cuello. La montura interior sigue la pose del torso.',18,INK)
    label(draw,(31,923),'Render con portador vanilla simplificado · no es una captura de Minecraft.',16,DIM)
    board.save(out/'capa_v1650_cuello.png',optimize=True)
