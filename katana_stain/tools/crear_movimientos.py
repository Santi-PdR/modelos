#!/usr/bin/env python3
"""Original test choreography, editable as poses in degrees. Not a mocap capture."""
import json
from pathlib import Path

out = Path(__file__).resolve().parents[1] / 'forge/resources/assets/stainkatana/player_animation'
# windup, contact, recovery: right-arm pitch/yaw/roll, torso yaw, left-arm pitch/roll
poses = [
    ((-125,-25,-65,35,-95,30),(-35,15,65,-35,-45,-15),(-15,0,10,-10,-25,-10)),
    ((-125,25,65,-35,-95,-30),(-35,-15,-65,35,-45,15),(-15,0,-10,10,-25,10)),
    ((-170,-10,-22,22,-130,20),(5,5,18,-18,-35,-8),(-25,0,8,0,-20,-10)),
    ((-175,5,10,-10,-145,-10),(20,0,-8,8,5,5),(-35,0,0,0,-25,0)),
    ((-145,-30,-45,40,-110,30),(-15,30,48,-32,-55,-5),(-30,0,12,0,-25,-10)),
    ((-145,30,45,-40,-110,-30),(-15,-30,-48,32,-55,5),(-30,0,-12,0,-25,10)),
    ((-165,-20,-30,20,-135,25),(10,10,25,-15,-30,-10),(-40,0,0,0,-35,-5)),
    ((-95,35,20,-25,-65,-15),(-95,-5,-8,8,-70,-8),(-45,0,0,0,-35,-8)),
    ((-95,-35,-20,25,-65,15),(-95,5,8,-8,-70,8),(-45,0,0,0,-35,8)),
    ((-175,0,0,0,-145,0),(30,0,0,0,10,0),(-35,0,0,0,-25,0)),
    ((-120,55,80,-70,-90,-35),(-20,-45,-70,75,-30,30),(-35,0,-10,0,-25,10)),
    ((-120,-55,-80,70,-90,35),(-20,45,70,-75,-30,-30),(-35,0,10,0,-25,-10)),
    ((-155,20,30,-25,-130,-15),(15,-15,-35,22,-20,15),(-35,0,0,0,-25,0)),
    ((-180,-10,-15,15,-160,10),(35,0,0,-5,20,0),(-40,0,0,0,-30,0)),
]
names = ['combo_1','combo_2','combo_3','combo_heavy'] + [f'scene_{i:02}' for i in range(1,11)]
for name, (wind, contact, recover) in zip(names, poses):
    def track(values):
        return {str(t): {'vector': v, 'easing': 'easeInOutSine'} for t,v in zip((0.0, 0.15, 0.3, 0.55),values)}
    def arm(p): return [p[0],p[1],p[2]]
    def left(p): return [p[4],0,p[5]]
    def body(p): return [0,p[3],0]
    clip = {'format_version':'1.8.0','animations':{name:{'animation_length':0.65,'bones':{
        'rightArm':{'rotation':track([arm(wind),arm(wind),arm(contact),arm(recover)])},
        'leftArm':{'rotation':track([left(wind),left(wind),left(contact),left(recover)])},
        'body':{'rotation':track([body(wind),body(wind),body(contact),body(recover)])},
        'torso':{'rotation':track([[0,wind[3]*.35,0],[5,wind[3]*.35,0],[-8,contact[3]*.35,0],[0,recover[3]*.35,0]])},
    }}}}
    (out / (name+'.json')).write_text(json.dumps(clip, indent=2)+'\n')
