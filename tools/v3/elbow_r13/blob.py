import numpy as np,sys;from PIL import Image
from scipy import ndimage as nd
for n in ('hair_back','hair_back_wave'):
    A=np.array(Image.open('/workspace/qa11/r13/%s_cur.png'%n)).astype(int)
    r,g,b,a=[A[...,i] for i in range(4)]
    pale=(a>200)&(r>235)&(g>200)&(b>190)
    m=np.zeros_like(pale);m[1450:1900,0:500]=1
    lab,k=nd.label(pale&(m>0)); sz=nd.sum(np.ones_like(lab),lab,range(1,k+1))
    big=lab==(np.argmax(sz)+1); print(n,sz.max(), np.argwhere(big).min(0),np.argwhere(big).max(0))
    big=nd.binary_dilation(big,iterations=2)&(a>0)&~((r<140)&(g<90))
    ring=nd.binary_dilation(big,iterations=12)&~big&(a>200)&~pale&(r>150)
    c=np.median(A[ring][:,:3],0); print(c)
    A[big,:3]=c
    Image.fromarray(A.astype(np.uint8)).save('/workspace/ssb/public/v3-demo/parts/%s.png'%n)
