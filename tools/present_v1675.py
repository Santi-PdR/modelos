"""Same-camera software plate for the folded elytra fit."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import cape_bloom as B
import cape_nocturne as N
import cape_wings as W
import preview_cloth as P
from present_v1590 import BG, DIM, INK, ROSE, STAGE, label


def plate(out, poses, wings, counts):
    sheet = Image.new('RGB', (1172, 738), BG)
    draw = ImageDraw.Draw(sheet)
    line = (77, 55, 79)
    slate = (109, 107, 130)
    label(draw, (29,24), 'MANTLE OF THE BLIGHT STAR   /   v1.67.5', 17, ROSE, bold=True)
    label(draw, (26,52), 'Holgura con élitros', 48, bold=True)
    label(draw, (30,115), 'Alas plegadas · misma fase, encuadre y luz en cada par.', 21, DIM)
    parts = (*P.MANNEQUIN_BOXES, *((W.profile()['origin'], W.profile()['size'], slate),)*2)
    transforms = [np.eye(4)]*6 + W.geometry(*wings)
    size, pitch, ambient = 307, 7, .59
    night = N.profile()
    gains = N.gains(night, N.darkness(night, 15*(ambient-.18)/.82), 1.22)
    h = P.effective_hidden(poses[0])
    render_options = dict(pitch=pitch, size=size, mannequin=parts, mannequin_pose=transforms,
                          bg=STAGE, ambient=ambient, emission=B.CORE, bloom=B.HALO, halo_gains=gains)
    allv = [W.hulls(*wings).reshape(-1,3)]
    allv += [points for m in poses for points,_,_ in P.collect(m,h)]
    allv += [np.array(o) + P.CORNERS*d for o,d,_ in P.MANNEQUIN_BOXES]
    for gi, (title, yaw) in enumerate((('DORSO · CUBRE EL ALA PLEGADA', 13), ('PERFIL · LA TELA QUEDA POR DETRÁS', -88))):
        left = 29 + 565*gi
        label(draw, (left,162), title, 18, INK, bold=True)
        v = np.concatenate(allv) @ (P.R('x',pitch) @ P.R('y',yaw))[:3,:3].T
        lo, hi = v.min(0), v.max(0)
        frame = (*(lo[:2]+hi[:2])/2, (size-27)/max(hi[:2]-lo[:2]))
        for j, model in enumerate(poses):
            x = left + j*272
            label(draw,(x,195),'SIN AJUSTE' if j==0 else 'CON AJUSTE', 16, DIM if j==0 else ROSE, bold=True)
            render = P.render(model, P.ARMOR_TEX, h, yaw=yaw, frame=frame, **render_options)
            sheet.paste(render.crop((21,0,286,size)), (x,222))
            draw.rectangle((x,222,x+264,528), outline=line if j==0 else ROSE)
    draw.rounded_rectangle((29,551,1143,685), radius=10, fill=STAGE, outline=line)
    old,new = counts
    label(draw,(48,566), f'−{100*(1-new[0]/old[0]):.0f}% cruces del paño libre', 25, ROSE, bold=True)
    label(draw,(48,607),'Medido con el volumen sólido del ala plegada.', 18, DIM)
    label(draw,(49,637),'Las puntas salen del volumen en las poses plegadas probadas.', 18, DIM)
    label(draw,(675,568),'Cuello y montura sin cambios', 23, bold=True)
    label(draw,(675,607),'El contacto cerca de la unión no se elimina.', 18, DIM)
    label(draw,(675,637),'Al abrir las alas se retira el ajuste.', 18, DIM)
    label(draw,(29,703),'Render software · Alas grises sin textura · No es una captura del juego.', 16, DIM)
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    sheet.save(out,optimize=True)
