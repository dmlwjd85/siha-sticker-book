# Round14: 허리 잘록 + 몸이 옷 옆선 밖으로 나오지 않게 + 발 정리. 항상 bak/ 원본에서 읽으므로 여러 번 돌려도 결과 같음.
import json,numpy as np
from PIL import Image
from scipy import ndimage as nd
P='/workspace/ssb/public/v3-demo/'; BK='/workspace/qa11/r14/bak/'
S=json.load(open(P+'skeleton.json')); AT={}
for slot,d in S['skins'][0]['attachments'].items():
    for k,v in d.items(): AT[k]=v
H,W=5120,2880
def load(n):
    v=AT[n]; im=np.array(Image.open(BK+v['path'].split('/')[-1]).convert('RGBA')).astype(float)
    C=np.zeros((H,W,4)); x,y=int(v['x']*2),int(v['y']*2); h,w=im.shape[:2]; C[y:y+h,x:x+w]=im; return C,(x,y,w,h)
BODY=['body_upper','body_upper_wave','body_lower','body_lower_wave']
GARM=['basic_upper','basic_upper_wave','basic_lower','basic_lower_wave']
L={n:load(n) for n in BODY+GARM}
A=lambda n:L[n][0][...,3]>100
Bm=np.zeros((H,W),bool); Gm=np.zeros((H,W),bool)
for n in BODY: Bm|=A(n)
for n in GARM: Gm|=A(n)
ANY=Bm|Gm
def seg(row,c):
    if not row[c]: return None
    l=c
    while l>0 and row[l-1]: l-=1
    r=c
    while r<W-1 and row[r+1]: r+=1
    return l,r
def gap(row,x,dx,lim=200):
    k=0
    while 0<x<W-1 and not row[x] and k<lim: x+=dx;k+=1
    return k
def warp_rows(img,rows):
    """rows: {y:(c,s,Rl,Rr,Tl,Tr)} 가로로만 c 기준 축소, 경계 밖 T 구간에서 0으로 줄어듦. 프리멀티 알파로 보간."""
    out=img.copy(); xs=np.arange(W,dtype=float)
    pm=img.copy(); pm[...,:3]*=pm[...,3:]/255.
    for y,(c,s,Rl,Rr,Tl,Tr) in rows.items():
        if s>=0.9999: continue
        f=xs.copy(); d=xs-c
        m=(d>=-Rl)&(d<=Rr); f[m]=c+d[m]*s
        dl=(1-s)*Rl; m=(d<-Rl)&(d>=-Rl-Tl); f[m]=xs[m]+dl*(1-(-Rl-d[m])/Tl)
        dr=(1-s)*Rr; m=(d>Rr)&(d<=Rr+Tr); f[m]=xs[m]-dr*(1-(d[m]-Rr)/Tr)
        src=np.interp(xs,f,xs)   # inverse map
        for ch in range(4): out[y,:,ch]=np.interp(src,xs,pm[y,:,ch])
    a=out[...,3:]; out[...,:3]=np.where(a>0,out[...,:3]/np.maximum(a,1e-6)*255.,0)
    return np.clip(out,0,255)
# ---- 1) 허리: 옷+몸 같이 잘록 (가우시안) ----
Y0,SG,AMT=2050,150,0.065
gr={};br={}
for y in range(1760,2420):
    g=np.exp(-((y-Y0)/SG)**2)
    c=1434
    sa=seg(ANY[y],c); sb=seg(Bm[y],c)
    if not sa or not sb: continue
    Rl,Rr=c-sa[0],sa[1]-c
    Tl=min(60,0.8*gap(ANY[y],sa[0]-1,-1)); Tr=min(60,0.8*gap(ANY[y],sa[1]+1,1))
    s=1-AMT*g
    # 테이퍼가 접히지 않게
    s=max(s,1-0.8*min(Tl/Rl,Tr/Rr)) if min(Tl,Tr)>2 else 1.0
    gr[y]=(c,s,Rl,Rr,max(Tl,1),max(Tr,1))
    br[y]=[c,s,c-sb[0],sb[1]-c,max(Tl+(sa[0]-sb[0])*0,1),max(Tr,1),sb]
# 몸 추가 축소: 옷이 있는 줄에서 몸 끝이 (축소 후) 옷 끝보다 3px 안쪽
k=np.ones(H)
for y,(c,s,Rl,Rr,Tl,Tr) in gr.items():
    if y<1840: continue
    sg=seg(Gm[y],c); sb=br[y][6]
    if not sg: continue
    gl=(c-sg[0])*s; grr=(sg[1]-c)*s; bl=(c-sb[0])*s; brr=(sb[1]-c)*s
    k[y]=min(1,(gl-3)/bl,(grr-3)/brr)
k=nd.minimum_filter1d(k,41); k=nd.gaussian_filter1d(k,12); k=np.minimum(k,1)
for y in br:
    c,s,Rl,Rr,Tl,Tr,sb=br[y]; s2=s*k[y]
    # 몸은 몸 바깥(옷 바깥까지 포함) T 안에서 0으로
    Tl2=Tl+(Rl-(c-sb[0]))*0; 
    s2=max(s2,1-0.8*min(Tl/Rl,Tr/Rr))
    br[y]=(c,s2,Rl,Rr,max(Tl,1),max(Tr,1))
# ---- 2) 발: 몸 발이 신발 밖으로 나오지 않게 (body_lower) ----
fr={}
Sh=A('basic_lower')|A('basic_lower_wave')
for (lo,hi) in ((900,1500),(1500,2400)):
    for y in range(4500,4900):
        b=np.where(Bm[y,lo:hi])[0]; f=np.where(Sh[y,lo:hi])[0]
        if len(b)==0 or len(f)==0: continue
        b=b+lo; f=f+lo; c=(f[0]+f[-1])/2
        need=min(1,(c-f[0]-4)/max(c-b[0],1),(f[-1]-4-c)/max(b[-1]-c,1))
        fr.setdefault(lo,{})[y]=(c,need,c-b[0],b[-1]-c)
footrows={}
for lo,d in fr.items():
    ys=sorted(d); need=np.array([d[y][1] for y in ys])
    ys=np.array(ys); need=np.where(ys<4575,1.0,np.clip(need,0.85,1))
    need=nd.minimum_filter1d(need,25); need=nd.gaussian_filter1d(need,16)
    ramp=np.clip((ys-4530)/50.,0,1); need=1-(1-need)*ramp
    for i,y in enumerate(ys):
        c,_,Rl,Rr=d[y]; s=min(1,need[i]-0.004)
        footrows.setdefault(y,[]).append((c,s,Rl,Rr,40,40))
def save(n,C):
    x,y,w,h=L[n][1]; Image.fromarray(C[y:y+h,x:x+w].round().astype(np.uint8)).save(P+AT[n]['path'])
for n in GARM:
    C=warp_rows(L[n][0],gr); save(n,C)
for n in BODY:
    C=warp_rows(L[n][0],br)
    if 'lower' in n:
        for side in (0,1):
            rows={y:v[side] for y,v in footrows.items() if len(v)>side}
            C=warp_rows(C,rows)
        # 맨발 발가락 줄 지우기: 발 안쪽(가장자리 8px 안) 진한 선 → 주변 살색
        a=C[...,3]>200; inner=nd.binary_erosion(a,iterations=9)
        Z=np.zeros_like(a); Z[4700:4900]=True
        dark=(C[...,:3].sum(-1)<520)&inner&Z
        dark=nd.binary_dilation(dark,iterations=3)&inner
        skin=inner&Z&~dark&(C[...,0]>230)
        idx=nd.distance_transform_edt(~skin,return_distances=False,return_indices=True)
        for ch in range(3): C[...,ch][dark]=C[...,ch][idx[0][dark],idx[1][dark]]
        # 채운 자리 줄무늬 없이: 주변 살색과 부드럽게 섞음
        zone=nd.binary_dilation(dark,iterations=12)&inner
        wgt=np.clip(nd.gaussian_filter(zone.astype(float),5)*1.6,0,1)*zone
        for ch in range(3):
            num=nd.gaussian_filter(C[...,ch]*(inner&~dark),14); den=nd.gaussian_filter((inner&~dark).astype(float),14)
            bl=num/np.maximum(den,1e-6); C[...,ch]=np.where(zone,C[...,ch]*(1-wgt)+bl*wgt,C[...,ch])
    save(n,C)
print('ok',min(v[1] for v in gr.values()),min(v[1] for v in br.values()),{y:v for y,v in list(footrows.items())[::60]})
