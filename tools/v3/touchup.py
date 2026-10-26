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
            g1=np.roll(g,o,ax); g2=np.roll(g,-o,ax); avg=np.where((l1>=l2)[...,None],g1,g2)   # 밝은 쪽 이웃색(어두운 덩어리 방지)
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
LINEC=np.array([110,61,91],np.float32)
def capsule(a,p,q,r,box):
    """상자 안을 둘레 바탕색(중앙값)으로 덮고, p→q 선을 둥근 끝(반지름 r, 안티에일리어싱)으로 다시 긋는다"""
    x0,y0,x1,y1=box; f=a.astype(np.float32); sub=f[y0:y1,x0:x1]
    ring=np.r_[f[y0-2:y0,x0:x1].reshape(-1,4),f[y0:y1,x0-2:x0].reshape(-1,4),f[y0:y1,x1:x1+2].reshape(-1,4)]
    ring=ring[(ring[:,3]>250)&(ring[:,:3].mean(1)>200)]; bg=np.median(ring[:,:3],0)
    yy,xx=np.mgrid[y0:y1,x0:x1]+0.5; p=np.array(p,float); q=np.array(q,float); d=q-p
    t=np.clip(((xx-p[0])*d[0]+(yy-p[1])*d[1])/(d@d),0,1); dist=np.hypot(xx-p[0]-t*d[0],yy-p[1]-t*d[1])
    L=np.clip(r+0.5-dist,0,1)[...,None]
    sub[...,:3]=bg*(1-L)+LINEC*L; f[y0:y1,x0:x1]=sub; return f.clip(0,255).astype(np.uint8)
def waist_line(a,x0,x1,yl,yr,hw=2.6,top=414,bot=446):
    """허리선(상의-치마 경계): x0..x1 에서 yl→yr 로 곧게 한 줄(폭 2*hw, 안티에일리어싱). 위는 그 열의 상의색, 아래는 치마색"""
    f=a.astype(np.float32)
    for x in range(x0,x1):
        yc=yl+(yr-yl)*(x-x0)/(x1-x0); sh=f[top-4:top,x,:3].mean(0); sk=f[bot:bot+4,x,:3].mean(0)
        for y in range(top,bot):
            d=abs(y+0.5-yc); L=np.clip(hw+0.5-d,0,1); base=sh if y+0.5<yc else sk
            f[y,x,:3]=base*(1-L)+LINEC*L; f[y,x,3]=255
    return f.clip(0,255).astype(np.uint8)
def unsmudge_hair(a,box,poly=None):
    """머리 가닥 사이 회색·진갈색 얼룩(채도 낮음, 외곽선 아님)을 둘레 분홍 머리색(정규화 가중 평균)으로 바꾼다. 외곽선(자두색)은 그대로"""
    import cv2
    x0,y0,x1,y1=box; f=a.astype(np.float32); s=f[y0:y1,x0:x1]; r,g,b,al=[s[...,i] for i in range(4)]
    plum=(r-g>35)&(b-g>12)&(s[...,:3].mean(-1)<130)
    pink=(r-g>40)&(b>g)&(s[...,:3].mean(-1)>165)&(al>250)
    m=(al>250)&~plum&~pink&((r-g<40)|(s[...,:3].mean(-1)<165))
    if poly is not None:
        pm=np.zeros(m.shape,np.uint8); cv2.fillPoly(pm,[np.array(poly,np.int32)-[x0,y0]],1); m&=pm>0
        edge=(pm>0)&(al>0)&(al<=250)&(r-g<40); s[...,3][edge]=0     # 틈 끝 회색 반투명 테 → 깨끗한 배경
    w=cv2.GaussianBlur(pink.astype(np.float32),(0,0),3); c=np.stack([cv2.GaussianBlur(s[...,i]*pink,(0,0),3) for i in range(3)],-1)/np.maximum(w,1e-3)[...,None]
    ok=m&(w>0.02); s[...,:3][ok]=c[ok]; s[...,3][ok]=255; f[y0:y1,x0:x1]=s; return f.clip(0,255).astype(np.uint8)
def reviewer_fixes():
    """검수 지적 1·2·5·6행(400% 비교) 손질. 좌표는 쉬는 자세 조각 기준 → 흔들기 짝 조각은 무대 좌표로 옮겨 같은 자리에"""
    def sh(slot,base,n):
        a,b=SK[slot][base],SK[slot][n]; return a['x']-b['x'],a['y']-b['y']
    for slot,base,fn in (('body_lower','body_lower',lambda a,dx,dy: capsule(a,(645.0+dx,97.5+dy),(645.5+dx,112+dy),2.0,(634+dx,84+dy,658+dx,108+dy))),
                         ('fit_upper','basic_upper',lambda a,dx,dy: waist_line(a,262+dx,352+dx,430.0+dy,430.5+dy,top=414+dy,bot=446+dy)),
                         ('hair_back','hair_back',lambda a,dx,dy: unsmudge_hair(unsmudge_hair(a,(664+dx,396+dy,692+dx,438+dy),poly=[(670+dx,398+dy),(680+dx,398+dy),(686+dx,420+dy),(684+dx,440+dy),(671+dx,440+dy)]),(756+dx,648+dy,790+dx,714+dy)))):
        for n in (base,base+'_wave'):
            if n not in SK[slot]: continue
            dx,dy=sh(slot,base,n); a=load(n)
            try: save(n,fn(a,dx,dy))
            except (ValueError,IndexError): print('건너뜀',n)
def cut_rest_forearm():
    """마이크 든 아래팔은 restPose로 팔꿈치에서 내려 그리므로, 몸 그림 속 옛 아래팔·주먹(hand_r 자리)을 지운다.
    그 뒤는 팔 내린 머리 그림(hair_armdown.jpg)으로 채운 머리가 보인다. 팔꿈치 둘레·얼굴(x>=560)은 남김. 지우기만."""
    h=SK['hand_r']['hand_r']; H=ndimage.binary_dilation(load('hand_r')[...,3]>0,iterations=4)
    ex,ey=412,988
    for n in ('body_upper','body_upper_wave'):
        t=SK['body_upper'][n]; a=load(n); m=np.zeros(a.shape[:2],bool)
        ys,xs=np.where(H); ys=ys+h['y']-t['y']; xs=xs+h['x']-t['x']; ok=(ys>=0)&(xs>=0)&(ys<a.shape[0])&(xs<a.shape[1]); m[ys[ok],xs[ok]]=True
        yy,xx=np.mgrid[0:a.shape[0],0:a.shape[1]]; X=xx+t['x']; Y=yy+t['y']
        m&=~(np.hypot(X-ex,Y-ey)<80)&(X<560)
        a[...,3]=np.where(m,0,a[...,3]); save(n,a)
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
    reviewer_fixes()
    cut_rest_forearm()
    sync_twins()
    print('touchup ok')
