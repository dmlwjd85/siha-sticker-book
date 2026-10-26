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
POLY=[('hand_r',[(135,91),(146,91),(146,107),(135,107)]),('hand_r',[(131,97),(134,97),(134,125),(131,125)]),('hand_r',[(131,115),(139,115),(139,117),(131,117)]),('body_lower',[(626,74),(639,74),(639,90),(626,90)]),('hand_r',[(131,93),(145,93),(145,103),(131,103)]),('hand_r',[(131,110),(139,110),(139,117),(131,117)]),('hand_r',[(131,117),(139,117),(134,133),(131,133)])]   # 엄지 아래 가로 막대·분홍 틈 → 엄지 주름 한 줄만 남김
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
def tame_white(a):
    """머리카락 위 하얀 줄(채도 낮고 밝은 픽셀)을 주변 머리색 중앙값으로 — 결 사이 밝은 줄·잘린 자리 흰 테"""
    g=a[...,:3].astype(int); L=g.mean(-1); sat=g.max(-1)-g.min(-1); A=a[...,3]>200
    w=A&(L>205)&(sat<60)
    if not w.any(): return a
    med=np.stack([ndimage.median_filter(np.where(w,np.nan_to_num(0),g[...,c]),size=9) for c in range(3)],-1)
    ok=A&~w; out=a.copy()
    for c in range(3):
        num=ndimage.uniform_filter(np.where(ok,g[...,c],0).astype(float),9); den=ndimage.uniform_filter(ok.astype(float),9)
        out[...,c]=np.where(w&(den>0.05),np.clip(num/np.maximum(den,1e-6),0,255),a[...,c]).astype(np.uint8)
    return out
def fill_slivers(a, it=2, offs=(2,3,4), box=None):
    """두 진한 선 사이에 낀 1~2px 밝은 줄(검사기 '이음새'와 같은 기준: 양옆 2px보다 14 넘게 밝음)을 양옆 평균색으로"""
    for _ in range(it):
        g=a[...,:3].astype(float); L=g.mean(-1); inner=ndimage.binary_erosion(a[...,3]>200,iterations=3)
        if box is not None: inner&=box
        for ax,o in [(ax,o) for ax in (1,0) for o in offs]:
            l1=np.roll(L,o,ax); l2=np.roll(L,-o,ax); m=inner&(L-np.maximum(l1,l2)>14)&(np.maximum(l1,l2)<150)
            avg=(np.roll(g,o,ax)+np.roll(g,-o,ax))/2
            a[...,:3][m]=avg[m].astype(np.uint8); L=a[...,:3].astype(float).mean(-1); g=a[...,:3].astype(float)
    return a
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
    return a
BOX=json.load(open(f'{HERE}/../../public/v3-demo/skeleton.json'))['animations']['wave']['changeBox']
TWINS=[('hair_back','hair_back','hair_back_wave'),('body_lower','body_lower','body_lower_wave'),('body_upper','body_upper','body_upper_wave'),('fit_lower','basic_lower','basic_lower_wave'),('fit_upper','basic_upper','basic_upper_wave')]
def sync_twins():
    """흔들기 층을 쉬는 층과 맞춤: 흔드는 팔 상자(changeBox) 밖 픽셀은 쉬는 층 그대로 복사(손질 차이로 생긴 잔상 방지)"""
    x0,y0,x1,y1=BOX
    for slot,r,w in TWINS:
        tr=SK[slot][r]; tw=SK[slot][w]; R=load(r); W=load(w)
        assert (tr['x'],tr['y'])==(tw['x'],tw['y'])
        h=min(R.shape[0],W.shape[0]); ww=min(R.shape[1],W.shape[1])
        yy,xx=np.mgrid[0:h,0:ww]; out=~((xx+tw['x']>=x0)&(xx+tw['x']<x1)&(yy+tw['y']>=y0)&(yy+tw['y']<y1))
        W[:h,:ww][out]=R[:h,:ww][out]
        if W.shape[1]>ww:  # 쉬는 층보다 넓은 부분은 상자 밖이면 비움
            yy2,xx2=np.mgrid[0:W.shape[0],ww:W.shape[1]]; o2=~((xx2+tw['x']>=x0)&(yy2+tw['y']>=y0)&(yy2+tw['y']<y1)); W[:,ww:][o2]=0
        save(w,W)
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
    t=SK['hair_back']['hair_back']; x0,y0,x1,y1=BOX
    for n in ('hair_back','hair_back_wave'):
        a=load(n); yy,xx=np.mgrid[0:a.shape[0],0:a.shape[1]]
        bx=(xx+t['x']>=x0-8)&(yy+t['y']>=y0)&(yy+t['y']<y1)   # 흔드는 팔이 비켜 가며 드러나는 머리 부분만
        save(n,fill_slivers(a,box=bx))
    sync_twins()
    print('touchup ok')
