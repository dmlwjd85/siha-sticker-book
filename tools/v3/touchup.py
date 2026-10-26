"""조각 마감 손질(그림을 새로 그리지 않고, 생성 그림의 얼룩·떠도는 선만 지움). build_v3.py 다음에 실행.
좌표는 각 조각 PNG 안의 픽셀(2배 크기)."""
import sys, os, numpy as np, cv2
from PIL import Image
from scipy import ndimage
HERE=os.path.dirname(os.path.abspath(__file__)); P=(sys.argv[1] if len(sys.argv)>1 else f'{HERE}/out')+'/parts'
# (조각, 상자) : 상자 안에서 바탕색과 다른 얼룩·짧은 선을 주변 색으로 메움
ERASE=[
 ('body_lower',(628,56,666,97)),          # 내린 주먹 손바닥 주름 얼룩
 ('basic_upper',(300,405,345,427)),('basic_upper',(300,437,316,448)),            # 허리 위 작은 선, 허리선 아래 삐침
 ('basic_upper_wave',(300,405,345,427)),('basic_upper_wave',(300,437,316,448)),
 
 ('body_lower',(649,90,662,103)),('body_lower',(640,82,652,93)),
 ('basic_upper',(303,420,320,428)),('basic_upper',(303,437,314,444)),
 ('basic_upper_wave',(303,420,320,428)),('basic_upper_wave',(303,437,314,444)),             # 엄지 아래 삐침
]
def load(n): return np.array(Image.open(f'{P}/{n}.png').convert('RGBA'))
def save(n,a): Image.fromarray(a).save(f'{P}/{n}.png')
def erase(a,box):
    x0,y0,x1,y1=box; c=a[y0:y1,x0:x1,:3].astype(int); A=a[y0:y1,x0:x1,3]>128
    lum=c.sum(-1); fill=np.median(c[A&(lum>=np.percentile(lum[A],60))],0)
    m=np.zeros(a.shape[:2],np.uint8); m[y0:y1,x0:x1]=((np.abs(c-fill).sum(-1)>40)&A)*255
    m=cv2.dilate(m,np.ones((3,3),np.uint8))
    a[...,:3]=cv2.inpaint(np.ascontiguousarray(a[...,:3]),m,4,cv2.INPAINT_TELEA); return a
# (조각, 다각형): 다각형 안을 모두 주변 색으로 메움(바깥선은 다각형 밖에 둠)
POLY=[('hand_r',[(131,93),(145,93),(145,103),(131,103)]),('hand_r',[(131,110),(139,110),(139,117),(131,117)]),('hand_r',[(131,117),(139,117),(134,133),(131,133)])]   # 엄지 아래 가로 막대·분홍 틈 → 엄지 주름 한 줄만 남김
def erase_poly(a,pts):
    m=np.zeros(a.shape[:2],np.uint8); cv2.fillPoly(m,[np.array(pts,np.int32)],1)
    g=a[...,:3].astype(int); L=g.mean(-1); A=a[...,3]>200
    near=cv2.dilate(m,np.ones((17,17),np.uint8)).astype(bool)&~m.astype(bool)
    skin=np.median(g[A&near&(L>200)],0)
    soft=cv2.GaussianBlur(m.astype(np.float32),(5,5),1.2)[...,None]
    a[...,:3]=np.clip(g*(1-soft)+skin*soft,0,255).astype(np.uint8); return a
def main_only(a):
    A=a[...,3]>40; lb,n=ndimage.label(A)
    if n>1:
        sz=ndimage.sum(A,lb,range(1,n+1)); keep=lb==(np.argmax(sz)+1); a[...,3]=np.where(keep,a[...,3],0)
    return a
def soften_ridges(a, it=3):
    """머리카락 결 사이 1~2px 밝은 줄(양옆보다 18 넘게 밝음)을 양옆 색으로 낮춤"""
    for _ in range(it):
        g=a[...,:3].astype(np.float32); L=g.mean(-1); A=a[...,3]>128
        out=g.copy(); hit=np.zeros(L.shape,bool)
        for ax in (0,1):
            p,q=np.roll(L,2,ax),np.roll(L,-2,ax); r=(L-np.maximum(p,q)>12)&A
            nb=(np.roll(g,2,ax)+np.roll(g,-2,ax))/2; out[r]=nb[r]; hit|=r
        a[...,:3]=np.clip(out,0,255).astype(np.uint8)
        if not hit.any(): break
    return a
import json
SK=json.load(open(f'{HERE}/../../public/v3-demo/skeleton.json'))['skins'][0]['attachments']
def union_holes(names):
    U=np.zeros((2560,1440),bool)
    for slot,n in names:
        t=SK[slot][n]; al=np.array(Image.open(f'{P}/{n}.png').convert('RGBA'))[...,3]>128
        U[t['y']:t['y']+al.shape[0],t['x']:t['x']+al.shape[1]]|=al
    return ndimage.binary_fill_holes(U)&~U
REST=[('hair_back','hair_back'),('body_lower','body_lower'),('body_upper','body_upper'),('fit_lower','basic_lower'),('fit_upper','basic_upper'),('hair_front','hair_front'),('hand_r','hand_r')]
WAVE=[('hair_back','hair_back_wave'),('body_lower','body_lower_wave'),('body_upper','body_upper_wave'),('fit_lower','basic_lower_wave'),('fit_upper','basic_upper_wave'),('hair_front','hair_front'),('hand_r','hand_r')]
def clear_pocket_rims(a,n=None):
    """머리카락 고리 안쪽 빈칸(모든 조각을 겹친 뒤에도 비는 곳) 가장자리의 흰 테(후광)를 투명하게"""
    A=a[...,3]>128; h=ndimage.binary_fill_holes(A)&~A
    for names in (REST,WAVE):
        slot=[s for s,m in names if m==n]
        if slot:
            t=SK[slot[0]][n]; H=union_holes(names); h|=H[t['y']:t['y']+A.shape[0],t['x']:t['x']+A.shape[1]]
    ring=ndimage.binary_dilation(h,iterations=5)&(a[...,3]>0)
    g=a[...,:3].astype(int); L=g.mean(-1); sat=g.max(-1)-g.min(-1)
    cand=ring&(((L>185)&(sat<70))|((L>135)&(sat<35)))
    lb,_=ndimage.label(cand|h); ok=np.unique(lb[h]); white=np.isin(lb,ok[ok>0])&cand
    a[...,3]=np.where(white,0,a[...,3])
    grey=ring&~white&(sat<40)&(L>70)&(a[...,3]>0)
    a[...,:3][grey]=(110,61,91); return a
if __name__=='__main__':
    by={}
    for n,b in ERASE: by.setdefault(n,[]).append(b)
    for n,bs in by.items():
        a=load(n)
        for b in bs: a=erase(a,b)
        save(n,a)
    for n,pts in POLY: save(n,erase_poly(load(n),pts))
    save('hand_r',main_only(load('hand_r')))
    for n in ('hair_back','hair_back_wave','hair_front'): save(n,clear_pocket_rims(soften_ridges(load(n)),n))
    print('touchup ok')
