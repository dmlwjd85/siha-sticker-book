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
 ('hand_r',(132,88,150,104)),('hand_r',(133,92,147,107)),
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
if __name__=='__main__':
    by={}
    for n,b in ERASE: by.setdefault(n,[]).append(b)
    for n,bs in by.items():
        a=load(n)
        for b in bs: a=erase(a,b)
        save(n,a)
    save('hand_r',main_only(load('hand_r')))
    for n in ('hair_back','hair_back_wave','hair_front'): save(n,soften_ridges(load(n)))
    print('touchup ok')
