# 2단계 리그: c3를 서로 겹치지 않는 영역으로 나눔(외곽선은 한 레이어에만). 지우기·마스크·처리값만 사용.
import json,numpy as np
from PIL import Image,ImageDraw
S=2
src=Image.open('/workspace/siha-v4/rebuild/body_F_c14.jpg').convert('RGB').resize((1440,2560),Image.LANCZOS)
a=np.asarray(src).astype(float);r,g,b=a[...,0],a[...,1],a[...,2]
gd=g-np.maximum(r,b)                      # 초록 우세도
alpha=np.clip(1-(gd-20)/60,0,1)           # 키 처리값
rgb=a.copy();sp=np.maximum(r,b);rgb[...,1]=np.minimum(g,sp)  # 스필 제거
from scipy.ndimage import binary_dilation as _bd
_bg=alpha<0.5;_lum=a.min(2)
_rim=_bg.copy()
for _ in range(6): _rim=_rim|(_bd(_rim)&(_lum>150))   # 배경에서 밝은 픽셀로만 이어지는 테(외곽선 넘지 않음)
alpha[_rim&~_bg]=0
_near=_bd(_rim,iterations=2)&~_rim
_e=_near&(rgb.max(2)<140);_m=rgb.min(2)[_e]*0.6
for c in range(3): rgb[...,c][_e]=_m                 # 외곽선 초록 번짐 무채색화
def poly(pts):
    m=Image.new('L',(1440,2560),0);ImageDraw.Draw(m).polygon([(x*S,y*S) for x,y in pts],fill=255);return np.asarray(m)>0
armL=poly([(0,280),(258,280),(258,342),(270,346),(268,442),(255,535),(0,535)])
armR=poly([(422,342),(720,342),(720,800),(460,800),(450,640),(427,520),(422,410)])
head=poly([(258,0),(720,0),(720,342),(460,342),(440,336),(260,336)])&~armL
from scipy.ndimage import binary_dilation
_b=~(armL|armR|head)
body=_b|(binary_dilation(_b,iterations=14)&(armL|armR))|(binary_dilation(_b,iterations=14)&head)
from scipy.ndimage import distance_transform_edt
def ramp(m):  # 팔의 몸 쪽 자른 면을 8px 알파 램프로(처리 값)
    d=distance_transform_edt(m);return np.clip(d/8,0,1)
cutL=ramp(armL|(alpha<0.5)) ; cutR=ramp(armR|(alpha<0.5)) ; cutH=ramp(head|(alpha<0.5))
out={}
for n,m in [('body',body),('arm_L',armL*cutL),('arm_R',armR*cutR),('head',head*cutH)]:
    A=(alpha*m*255).astype(np.uint8)
    im=np.dstack([rgb.astype(np.uint8),A]);ys,xs=np.nonzero(A)
    x0,y0,x1,y1=xs.min(),ys.min(),xs.max()+1,ys.max()+1
    Image.fromarray(im[y0:y1,x0:x1],'RGBA').save(f'/workspace/ssb/public/v4c-demo/parts/{n}.png')
    out[n]=dict(x=int(x0),y=int(y0),width=int(x1-x0),height=int(y1-y0))
sk={"skeleton":{"width":1440,"height":2560,"scale":2,"note":"v4c: c14 원본(GenerateImage) 2배 Lanczos(4단계에서 Real-ESRGAN 4x로 교체 예정) → 초록 키+스필 제거 → 4영역(몸·머리·왼팔·오른팔), 몸은 팔 아래로 14px 마스크 확장해 제자리 피부를 깔고 팔이 위에 얹힘. 팔 피벗=실제 어깨 관절. 외곽선은 한 레이어에만 있음."},
 "bones":[{"name":"root","rest":{"x":720,"y":1280}},{"name":"head","parent":"root","rest":{"x":340*S,"y":336*S}},{"name":"arm_L","parent":"root","rest":{"x":272*S,"y":372*S}},{"name":"arm_R","parent":"root","rest":{"x":425*S,"y":372*S}}],
 "slots":[dict(name=n,bone={'body':'root'}.get(n,n),path=f'parts/{n}.png',**out[n]) for n in ['body','arm_R','arm_L','head']],
 "items":[],"animations":{"wave":{"bone":"arm_L","period":1.6,"repeat":2,"angle":[[0,0],[0.4,3],[0.8,-1.5],[1.2,3],[1.6,0]]}}}
json.dump(sk,open('/workspace/ssb/public/v4c-demo/skeleton.json','w'),ensure_ascii=False)
# 회전 시 빈 영역 측정
def comp(ang):
    c=Image.new('RGBA',(1440,2560),(0,0,0,0))
    for n in ['body','arm_R','arm_L','head']:
        p=Image.open(f'/workspace/ssb/public/v4c-demo/parts/{n}.png');o=out[n];L=Image.new('RGBA',(1440,2560));L.paste(p,(o['x'],o['y']));L=L.convert('RGBa')
        if n=='arm_L':L=L.rotate(ang,center=(272*S,372*S),resample=Image.BILINEAR)
        L=L.convert('RGBA')
        c=Image.alpha_composite(c,L)
    return c
base=np.asarray(comp(0))[...,3].astype(int)
for ang in [3,-1.5]:
    pass
for ang in [3,-1.5]:
    c=comp(ang);A=np.asarray(c)[...,3].astype(int)
    hole=(base>200)&(A<200)&poly([(230,320),(320,320),(320,460),(230,460)])
    print(ang,'shoulder holes',hole.sum());c.save(f'/tmp/v4c/comp_{ang}.png')
