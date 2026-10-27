"""가장자리·점 마감(그림을 새로 그리지 않음). touchup.py 다음에 실행.
1) 떨어진 작은 조각(점)·작은 구멍 지우기
2) 알파 매팅: 가위로 자른 듯 들쭉날쭉한 가장자리를 곡선으로 매끈하게(약 2px 부드러운 안티에일리어싱)
3) 머리카락·신발 흐림 완화(약한 언샤프)·내부의 떠도는 진한 점 지우기
사용: python3 tools/v3/clean_edges.py [parts 폴더]"""
import sys, os, numpy as np, cv2
from PIL import Image
from scipy import ndimage
HERE=os.path.dirname(os.path.abspath(__file__))
P=sys.argv[1] if len(sys.argv)>1 else f'{HERE}/../../public/v3-demo/parts'
SHARP={'hair_back','hair_back_wave','hair_front','body_lower','body_lower_wave'}
SPECK={'hair_back','hair_back_wave','hair_front','body_lower','body_lower_wave'}
def ext_rgb(rgb,a):
    """투명 쪽 색을 가장자리 색으로 채움(가장자리 테두리 색 번짐 방지)"""
    w=(a>0.02).astype(np.float32)   # 반투명 선 픽셀 색은 그대로(바꾸면 가는 선이 점선이 됨)
    num=cv2.GaussianBlur(rgb*w[...,None],(0,0),3); den=cv2.GaussianBlur(w,(0,0),3)[...,None]
    fill=num/np.maximum(den,1e-4); return np.where(w[...,None]>0.5,rgb,fill)
def matte(a):
    A=a>0.5
    lb,n=ndimage.label(A)
    if n>1:
        sz=ndimage.sum(A,lb,range(1,n+1)); A=np.isin(lb,1+np.where(np.array(sz)>=400)[0])
    H=ndimage.binary_fill_holes(A)&~A; lb,n=ndimage.label(H)
    if n:
        sz=ndimage.sum(H,lb,range(1,n+1)); A|=np.isin(lb,1+np.where(np.array(sz)<60)[0])
    f=cv2.GaussianBlur(A.astype(np.float32),(0,0),1.0)
    t=np.clip((f-0.3)/0.4,0,1); return t*t*(3-2*t)
def despeck(rgb,A):
    L=rgb.mean(-1); dark=(L<120)&A; lb,n=ndimage.label(dark)
    if not n: return rgb
    sz=ndimage.sum(dark,lb,range(1,n+1)); small=np.isin(lb,1+np.where(np.array(sz)<=6)[0])
    near=cv2.dilate((dark&~small).astype(np.uint8),np.ones((9,9),np.uint8)).astype(bool); small&=~near   # 선 조각은 남기고 떨어진 점만
    small=cv2.dilate(small.astype(np.uint8),np.ones((3,3),np.uint8))
    return cv2.inpaint(np.clip(rgb,0,255).astype(np.uint8),small,3,cv2.INPAINT_TELEA).astype(np.float32)
for f in sorted(os.listdir(P)):
    if not f.endswith('.png'): continue
    n=f[:-4]; im=np.array(Image.open(f'{P}/{f}').convert('RGBA')).astype(np.float32)
    rgb,a=im[...,:3],im[...,3]/255
    if n in SPECK: rgb=despeck(rgb,ndimage.binary_erosion(a>0.5,iterations=4))
    if n in SHARP:
        rgb=cv2.bilateralFilter(rgb.astype(np.float32),7,22,4); bl=cv2.GaussianBlur(rgb,(0,0),1.2); rgb=np.clip(rgb+0.45*(rgb-bl),0,255)   # 압축 얼룩을 먼저 눌러야 날카롭게 해도 점이 안 생김
    na=a if n=='hair_front' else matte(a); rgb=ext_rgb(rgb,a)   # 앞머리는 가는 결 끝이 많아 touchup.hair_edge_aa 결과를 그대로 씀
    out=np.dstack([np.clip(rgb,0,255),na*255]).round().astype(np.uint8)
    Image.fromarray(out).save(f'{P}/{f}',optimize=True)
    print(n,'ok')
