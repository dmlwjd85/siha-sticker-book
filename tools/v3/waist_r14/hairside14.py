# Round14 허리 옆: hair_back(_wave) 안에 구워져 있던 '흰 몸통 실루엣+외곽선'(옛 몸 옆선)을 지움.
# 몸을 잘록하게 줄이자 이 흰 몸통이 몸 옆으로 삐져나와 보였음. bak/ 에서 읽음(멱등).
import numpy as np
from PIL import Image
from scipy import ndimage as nd
P='/workspace/ssb/public/v3-demo/parts/'; BK='/workspace/qa11/r14/bak/'
for n in ('hair_back','hair_back_wave'):
    a=np.array(Image.open(BK+n+'.png').convert('RGBA'))
    r,g,b,al=[a[...,i].astype(int) for i in range(4)]
    wh=(al>0)&(r>200)&(g>185)&(b>185)&(r-g<35)          # 흰/연한 몸통색
    lb,nn=nd.label(wh); objs=nd.find_objects(lb); sz=nd.sum(wh,lb,range(1,nn+1))
    ids=[i+1 for i,sl in enumerate(objs) if sl[0].start>=1100 and sz[i]>500]   # 목 아래(몸통) 덩어리만
    body=np.isin(lb,ids); body=nd.binary_closing(body,iterations=3)|body
    pink=(al>0)&(r-g>40)&(r>150)&~body
    nearpink=nd.binary_dilation(pink,iterations=3)
    dark=(al>0)&(r<170)&~pink
    kill=body|(dark&nd.binary_dilation(body,iterations=12)&~nearpink)
    # 가장자리 안티앨리어싱 잔여(반투명 픽셀)도 같이
    kill|=nd.binary_dilation(kill,iterations=2)&(al<200)&~nearpink
    # 작은 떠 있는 조각 제거
    rem=(al>0)&~kill; l2,n2=nd.label(rem); s2=nd.sum(rem,l2,range(1,n2+1))
    kill|=np.isin(l2,[i+1 for i,v in enumerate(s2) if v<300])&(np.arange(a.shape[0])[:,None]>=1100)
    a[...,3][kill]=0
    print(n,'comps',len(ids),'kill',int(kill.sum()))
    Image.fromarray(a).save(P+n+'.png')
