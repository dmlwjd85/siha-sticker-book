import json,sys,numpy as np
from PIL import Image
P=json.load(open('out/parts.json')); OUT='out'
MIC=dict(scale=0.2,rot=-12,cx=506,cy=618,grip=0.5)   # 2배 좌표
def compose(outfit=True,wave=False,eyes=False,mic=True,fa_rot=0,bg=(253,238,246)):
    c=Image.new('RGBA',(1440,2560),bg+(255,))
    def put(k,im=None,pos=None):
        p=P[k]; im=im or Image.open(f"{OUT}/{p['path']}"); c.alpha_composite(im,pos or (p['x'],p['y']))
    put('hair_back'); put('pelvis_wave' if wave else 'pelvis')
    if outfit: put('basic_pelvis_wave' if wave else 'basic_pelvis')
    put('chest_wave' if wave else 'chest')
    if outfit: put('basic_chest_wave' if wave else 'basic_chest')
    if wave:
        fr=min(P['wave_frames'],key=lambda f:abs(f['angle']-fa_rot))
        for nm in (['body','basic'] if outfit else ['body']):
            p=fr[nm]; c.alpha_composite(Image.open(f"{OUT}/{p['path']}"),(p['x'],p['y']))
    if eyes: put('eyes_closed')
    put('hair_front')
    if mic:
        m=Image.open(f'{OUT}/parts/prop_mic.png'); w,h=m.size; s=MIC['scale']; m=m.resize((round(w*s),round(h*s)),Image.LANCZOS)
        L=Image.new('RGBA',(1440,2560)); gx,gy=m.size[0]/2,m.size[1]*MIC['grip']; L.alpha_composite(m,(round(MIC['cx']-gx),round(MIC['cy']-gy)))
        L=L.rotate(-MIC['rot']*-1,Image.BICUBIC,center=(MIC['cx'],MIC['cy'])); c.alpha_composite(L)
    put('hand_r')
    return c
if __name__=='__main__':
    c=compose(); c.convert('RGB').save('/tmp/p_full.png'); c.crop((300,300,800,800)).save('/tmp/p_mic.png')
    c.convert('RGB').resize((390,693),Image.LANCZOS).save('/tmp/p_small.png')
