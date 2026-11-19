"""Fixed-camera bloom comparison and motion curves measured from Java."""
from PIL import Image, ImageDraw

import cape_bloom as B
import cape_nocturne as N
import preview_cloth as P
from present_v1590 import BG, DIM, INK, ROSE, STAGE, fit_frame, label

LINE = (77, 55, 79)
LAVENDER = (175, 150, 218)


def chart(draw, x, title, rows):
    y = 690
    draw.rounded_rectangle((x,y,x+525,y+204), radius=10, fill=STAGE, outline=LINE)
    label(draw, (x+16,y+10), title, 17, INK, bold=True)
    left, base, w, h = x+50, y+166, 453, 118
    for value, tick in ((0, '0°'), (1, '1°'), (2, '2°')):
        pos = base - h*value/2.1
        draw.line((left,pos,left+w,pos), fill=LINE)
        label(draw, (x+16,pos-9), tick, 14, DIM)
    for t, tick in ((0,'0 s'),(.5,'0,5 s'),(1,'1 s')):
        pos = left+w*t
        label(draw, (pos-12,base+8), tick, 14, DIM)
    for column, color in ((-2,LAVENDER), (-1,ROSE)):
        points = [(left+w*row[0], base+h*row[column]/2.1) for row in rows if row[0] <= 1]
        draw.line(points, fill=color, width=3, joint='curve')


def plate(path, geo, data):
    p = N.profile()
    sheet = Image.new('RGB', (1120, 954), BG)
    d = ImageDraw.Draw(sheet)
    label(d, (29,23), 'MANTLE OF THE BLIGHT STAR   /   v1.67.3', 18, ROSE, bold=True)
    label(d, (26,53), 'Halo que responde a la luz', 48, bold=True)
    label(d, (30,119), 'Mismos cortes, pose y cámara. El halo no cambia el contorno.', 20, DIM)
    yaw, pitch, size = 25, 10, 480
    frame = fit_frame([geo], yaw, pitch, size, mannequin=True, margin=62)
    states = [('CUEVA', 'Sólo núcleo', .18, False), ('CUEVA', 'Halo reforzado', .18, True),
              ('LUZ CERCANA', 'Halo atenuado', .88, True), ('DÍA', 'Halo atenuado', 1, True)]
    for i, (title, line, ambient, bloom) in enumerate(states):
        x = 29 + i*269
        label(d, (x,164), title, 17, ROSE if i == 1 else DIM, bold=True)
        label(d, (x,190), line, 20, INK)
        view = P.render(geo, P.ARMOR_TEX, P.effective_hidden(geo), yaw=yaw, pitch=pitch, size=size,
                        frame=frame, bg=STAGE, mannequin=True, ambient=ambient, emission=B.CORE,
                        tint=(.932,.69,.91), bloom=B.HALO if bloom else None,
                        halo_gains=N.gains(p, N.darkness(p, 15*(ambient-.18)/.82), .61))
        crop = view.crop((114,22,366,458))
        sheet.paste(crop, (x,222))
        d.rectangle((x,222,x+251,657), outline=ROSE if i == 1 else LINE)
    label(d, (29,661), 'Apertura extra del último tramo', 19, INK, bold=True)
    d.line((687,674,712,674), fill=LAVENDER, width=3)
    label(d, (720,662), 'Antes', 16, DIM)
    d.line((807,674,832,674), fill=ROSE, width=3)
    label(d, (840,662), 'Retardo del dobladillo', 16, INK)
    chart(d, 29, 'FRENADA', data['BRAKE'])
    chart(d, 566, 'ATERRIZAJE', data['LAND'])
    d.line((29,915,1091,915), fill=LINE)
    label(d, (29,924), 'Diagnóstico del GEO y del filtro Java. El halo se queda sobre el paño; no ilumina el mundo.', 16, DIM)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, optimize=True)
