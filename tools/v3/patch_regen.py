"""흐린 부분 고해상도 조각 교체. 그림은 GenerateImage로 기존 부품 조각을 참조로 넣어 같은 구도로 다시 그린 것(raw/*_patch.jpg).
코드는 정렬(ECC 어파인)·배치·경계 블렌드만 한다. 부품 바깥 테두리(알파·외곽선)는 원래 것을 유지해 리그·검사 기준이 바뀌지 않는다.
clean_edges.py 다음에 실행. 사용: python3 tools/v3/patch_regen.py [parts 폴더]"""
import sys, os, numpy as np, cv2
from PIL import Image
from scipy import ndimage
HERE=os.path.dirname(os.path.abspath(__file__))
P=sys.argv[1] if len(sys.argv)>1 else f'{HERE}/../../public/v3-demo/parts'
# (조각 그림, 부품들, 로컬 상자 x0,y0,x1,y1, 테두리에서 안쪽으로 원본 유지 px)
JOBS=[('hair_back_ul_patch.jpg',['hair_back','hair_back_wave'],(0,200,400,600),4),
      ('hair_back_ur_patch.jpg',['hair_back','hair_back_wave'],(414,200,814,600),4),
      ('hair_back_lr_patch.jpg',['hair_back','hair_back_wave'],(454,600,814,1080),4),
      ('hair_front_patch.jpg',['hair_front'],(0,0,467,467),3),
      ('hair_elbow_patch.jpg',['hair_back','hair_back_wave'],(40,600,340,1000),6),   # 보는 사람 기준 왼쪽 팔꿈치 위 뒷머리 번짐
      ('shoe_l_patch.jpg',['basic_lower','basic_lower_wave'],(40,960,250,1169),3),
      ('shoe_r_patch.jpg',['basic_lower','basic_lower_wave'],(395,960,605,1169),3)]
ORIG={n[:-4]:np.array(Image.open(f'{P}/{n}').convert('RGBA')).astype(np.float32) for n in os.listdir(P) if n.endswith('.png')}
def same_as_base(n,box):
    """흔들기용 부품은 쉬는 자세 부품과 같은 픽셀에만 같은 조각을 넣는다(동작 전환 때 선명도가 튀지 않게, 다른 곳은 원래대로)"""
    b=n[:-5] if n.endswith('_wave') else None
    if b not in ORIG: return 1.0
    X0,Y0,x1,y1=box; d=np.abs(ORIG[n][Y0:y1,X0:x1]-ORIG[b][Y0:y1,X0:x1]).max(-1)
    return cv2.GaussianBlur((d<8).astype(np.float32),(0,0),1.0)
WARP={}
def gray(x): return cv2.GaussianBlur(cv2.cvtColor(np.clip(x,0,255).astype(np.uint8),cv2.COLOR_RGB2GRAY).astype(np.float32),(0,0),1.5)
for raw,parts,(X0,Y0,X1,Y1),keep in JOBS:
    gen=np.array(Image.open(f'{HERE}/raw/{raw}').convert('RGB')).astype(np.float32)
    for n in parts:
        f=f'{P}/{n}.png'
        if not os.path.exists(f): continue
        im=np.array(Image.open(f).convert('RGBA')).astype(np.float32); rgb,a=im[...,:3],im[...,3]/255
        x1,y1=min(X1,a.shape[1]),min(Y1,a.shape[0]); W,H=x1-X0,y1-Y0
        if (a[Y0:y1,X0:x1]>0.5).sum()<200: continue
        ref=rgb[Y0:y1,X0:x1]*a[Y0:y1,X0:x1,None]+220*(1-a[Y0:y1,X0:x1,None])
        g=cv2.resize(gen,(X1-X0,Y1-Y0),interpolation=cv2.INTER_AREA)[:H,:W]
        if raw in WARP and n.endswith('_wave'): cc,w=WARP[raw]   # 흔들기용 부품은 쉬는 자세 부품과 같은 정렬을 그대로 사용
        else:
            w=np.eye(2,3,dtype=np.float32)
            cc,w=cv2.findTransformECC(gray(ref),gray(g),w,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,300,1e-6),None,3)
            WARP[raw]=(cc,w)
        same=same_as_base(n,(X0,Y0,x1,y1))

        if cc<0.85: print(n,raw,'정렬 실패 → 원본 유지',round(float(cc),3)); continue
        g=cv2.warpAffine(g,w,(W,H),flags=cv2.INTER_LANCZOS4|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE)
        inner=ndimage.binary_erosion(a[Y0:y1,X0:x1]>0.99,iterations=keep).astype(np.float32)
        yy,xx=np.mgrid[0:H,0:W]; edge=np.minimum.reduce([xx,yy,W-1-xx,H-1-yy+(0 if y1<a.shape[0] else 99)]).astype(np.float32)
        m=cv2.GaussianBlur(inner,(0,0),1.5)*np.clip(edge/12,0,1)*same
        rgb[Y0:y1,X0:x1]=rgb[Y0:y1,X0:x1]*(1-m[...,None])+g*m[...,None]
        Image.fromarray(np.dstack([np.clip(rgb,0,255),a*255]).round().astype(np.uint8)).save(f,optimize=True)
        print(n,raw,'ecc',round(float(cc),3))
