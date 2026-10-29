import json,numpy as np
from PIL import Image
P='/workspace/ssb/public/v3-demo/'
S=json.load(open(P+'skeleton.json'))
AT={}
for slot,d in S['skins'][0]['attachments'].items():
    for k,v in d.items(): AT[k]=v
def place(name,src=None):
    v=AT[name]; im=np.array(Image.open(src or P+v['path']).convert('RGBA'))
    C=np.zeros((5120,2880,4),np.uint8); x,y=int(v['x']*2),int(v['y']*2)
    h,w=im.shape[:2]; C[y:y+h,x:x+w]=im; return C
def over(layers):
    out=np.zeros((5120,2880,4),float)
    for L in layers:
        a=L[...,3:]/255.; out[...,:3]=L[...,:3]*a+out[...,:3]*(1-a); out[...,3:]=a+out[...,3:]*(1-a)
    return out
