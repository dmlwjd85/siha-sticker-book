# 2단계 리그: c3를 서로 겹치지 않는 영역으로 나눔(외곽선은 한 레이어에만). 지우기·마스크·처리값만 사용.
import json,numpy as np
from PIL import Image,ImageDraw
S=2
src=Image.open('/workspace/siha-v4/rebuild/body_F_c3.jpg').convert('RGB').resize((1440,2560),Image.LANCZOS)
a=np.asarray(src).astype(float);r,g,b=a[...,0],a[...,1],a[...,2]
gd=g-np.maximum(r,b)                      # 초록 우세도
alpha=np.clip(1-(gd-20)/60,0,1)           # 키 처리값
rgb=a.copy();sp=np.maximum(r,b);rgb[...,1]=np.minimum(g,sp)  # 스필 제거(초록을 r/b 최대치로 제한)
def poly(pts):
    m=Image.new('L',(1440,2560),0);ImageDraw.Draw(m).polygon([(x*S,y*S) for x,y in pts],fill=255);return np.asarray(m)>0
armL=poly([(0,255),(268,255),(268,340),(276,345),(280,415),(255,520),(0,520)])
armR=poly([(424,330),(720,330),(720,750),(445,750),(440,560),(425,415)])
from scipy.ndimage import binary_dilation
body=binary_dilation(~(armL|armR),iterations=14)  # 몸 마스크를 팔 아래로 14px 넓혀 같은 자리 원본 피부를 깔아 둠(복사 아님)
from scipy.ndimage import distance_transform_edt
def ramp(m):  # 팔의 몸 쪽 자른 면을 8px 알파 램프로(처리 값)
    d=distance_transform_edt(m);return np.clip(d/8,0,1)
cutL=ramp(armL|(alpha<0.5)) ; cutR=ramp(armR|(alpha<0.5))
out={}
for n,m in [('body',body),('arm_L',armL*cutL),('arm_R',armR*cutR)]:
    A=(alpha*m*255).astype(np.uint8)
    im=np.dstack([rgb.astype(np.uint8),A]);ys,xs=np.nonzero(A)
    x0,y0,x1,y1=xs.min(),ys.min(),xs.max()+1,ys.max()+1
    Image.fromarray(im[y0:y1,x0:x1],'RGBA').save(f'/workspace/ssb/public/v4c-demo/parts/{n}.png')
    out[n]=dict(x=int(x0),y=int(y0),width=int(x1-x0),height=int(y1-y0))
sk={"skeleton":{"width":1440,"height":2560,"scale":2,"note":"v4c: c3 원본(GenerateImage) 2배 Lanczos(4단계에서 Real-ESRGAN 4x로 교체 예정) → 초록 키+스필 제거 → 3영역(몸·왼팔·오른팔), 몸은 팔 아래로 14px 마스크 확장해 제자리 피부를 깔고 팔이 위에 얹힘. 팔 피벗=실제 어깨 관절. 외곽선은 한 레이어에만 있음. 머리 분리는 미적용(몸에 포함)."},
 "bones":[{"name":"root","rest":{"x":720,"y":1280}},{"name":"arm_L","parent":"root","rest":{"x":276*S,"y":350*S}},{"name":"arm_R","parent":"root","rest":{"x":426*S,"y":345*S}}],
 "slots":[dict(name=n,bone={'body':'root'}.get(n,n),path=f'parts/{n}.png',**out[n]) for n in ['body','arm_R','arm_L']],
 "items":[],"animations":{"wave":{"bone":"arm_L","period":1.6,"repeat":2,"angle":[[0,0],[0.4,3],[0.8,-1.5],[1.2,3],[1.6,0]]}}}
json.dump(sk,open('/workspace/ssb/public/v4c-demo/skeleton.json','w'),ensure_ascii=False)
# 회전 시 빈 영역 측정
def comp(ang):
    c=Image.new('RGBA',(1440,2560),(0,0,0,0))
    for n in ['body','arm_R','arm_L']:
        p=Image.open(f'/workspace/ssb/public/v4c-demo/parts/{n}.png');o=out[n];L=Image.new('RGBA',(1440,2560));L.paste(p,(o['x'],o['y']));L=L.convert('RGBa')
        if n=='arm_L':L=L.rotate(ang,center=(276*S,350*S),resample=Image.BILINEAR)
        L=L.convert('RGBA')
        c=Image.alpha_composite(c,L)
    return c
base=np.asarray(comp(0))[...,3].astype(int)
for ang in [3,-1.5]:
    c=comp(ang);A=np.asarray(c)[...,3].astype(int)
    hole=(base>200)&(A<200)&poly([(240,300),(320,300),(320,440),(240,440)])
    print(ang,'shoulder holes',hole.sum());c.save(f'/tmp/v4c/comp_{ang}.png')
