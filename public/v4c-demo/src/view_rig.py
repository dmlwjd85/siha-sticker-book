import json,numpy as np
from PIL import Image
D='/workspace/ssb/public/v4c-demo/';sk=json.load(open(D+'skeleton.json'));B={b['name']:b['rest'] for b in sk['bones']}
def comp(rot):
    c=Image.new('RGBA',(1440,2560),(40,40,40,255))
    for s in sk['slots']:
        L=Image.new('RGBA',(1440,2560));L.paste(Image.open(D+s['path']),(s['x'],s['y']));L=L.convert('RGBa')
        a=rot.get(s['bone'],0)
        if a:L=L.rotate(a,center=(B[s['bone']]['x'],B[s['bone']]['y']),resample=Image.BILINEAR)
        c=Image.alpha_composite(c,L.convert('RGBA'))
    return c
for tag,rot in [('L3',{'arm_L':3}),('Lm',{'arm_L':-1.5}),('H2',{'head':2}),('Hm',{'head':-2})]:
    c=comp(rot)
    box=(400,840,600,1160) if tag[0]=='L' else (500,820,880,980)
    x=c.crop(box);x.resize((x.width*4,x.height*4),Image.NEAREST).save(f'/workspace/ssb/public/v4c-demo/src/crops/rig27_{tag}.png')
