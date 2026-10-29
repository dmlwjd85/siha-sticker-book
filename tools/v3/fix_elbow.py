"""보는 사람 기준 왼쪽 팔(오른팔, 마이크 쥔 팔) 위팔 바깥 이음새 정리.
cut_rest_forearm()으로 옛 아래팔을 지운 자리에 위팔 바깥선이 점선·직선 자름 자국·쐐기 홈으로 남아 '레이어 이음새'처럼 보였다.
새 그림을 그리지 않고, 같은 부품 안의 원래 바깥선과 같은 색·같은 굵기로 어깨 곡선 끝에서 팔꿈치(아래팔 조각 밑)까지 매끈하게 이어 준다.
점선 조각과 홈은 바로 옆 피부색으로 채운다. 대상: body_upper, body_upper_wave (원점 같음, 1배 부품 좌표).
사용: python3 tools/v3/fix_elbow.py [parts 폴더]   (touchup → clean_edges → patch_regen → fix_elbow → upscale_parts 순서)"""
import sys, os, numpy as np, cv2
from PIL import Image
from scipy import ndimage, interpolate
HERE=os.path.dirname(os.path.abspath(__file__))
P=sys.argv[1] if len(sys.argv)>1 else f'{HERE}/../../public/v3-demo/parts'
# 위팔 바깥선 기준점(body_upper 로컬 px). 위: 어깨 곡선 끝, 아래: 아래팔 조각(hand_r)이 덮는 팔꿈치 안
PTS=np.array([(141,588),(127,599),(116,616),(107,660),(105.5,715),(106,765),(102,798),(92,818),(76,834)],float)
HALF=2.6   # 원래 바깥선 반폭(px)
def fix(name):
    f=f'{P}/{name}.png'
    if not os.path.exists(f): return
    im=np.array(Image.open(f).convert('RGBA')).astype(np.float32); rgb,a=im[...,:3],im[...,3]/255
    tck,_=interpolate.splprep(PTS.T,s=2); u=np.linspace(0,1,2000); cx,cy=interpolate.splev(u,tck)
    H,W=a.shape; yy,xx=np.mgrid[0:H,0:W]
    y0,y1=int(PTS[0,1]),int(PTS[-1,1])
    # 곡선까지 거리
    pts=np.stack([cx,cy],1); line=np.zeros((H,W),np.uint8)
    cv2.polylines(line,[np.round(pts*16).astype(np.int32)],False,1,1,cv2.LINE_8,4)
    d=ndimage.distance_transform_edt(line==0)
    xc=np.interp(yy,cy,cx)          # 같은 높이의 곡선 x
    band=(yy>=y0-2)&(yy<=y1)&(xx<175)
    inside=band&(xx>=xc)             # 곡선 오른쪽 = 위팔
    # 1) 위팔 안쪽 6px 띠의 점선·자름 자국을 피부색으로
    skin_src=inside&(xx>xc+9)&(xx<xc+40)&(a>0.99)&(rgb.mean(-1)>200)
    _,(iy,ix)=ndimage.distance_transform_edt(~skin_src,return_indices=True)
    fillm=inside&(yy>=612)&((xx<xc+9)|(a<0.99))&(xx<xc+40)
    fillm&=~((rgb.mean(-1)<200)&(xx>xc+9))   # 몸통선 등 다른 선은 그대로
    rgb[fillm]=rgb[iy,ix][fillm]; a[fillm]=1
    # 2) 곡선 바깥(왼쪽)은 투명, 경계는 부드럽게
    sd=np.where(inside,d,-d)         # 위팔 쪽 +
    outside=band&~inside&(yy>=616)&(xx>xc-30)
    a[outside]=np.clip(0.5+sd[outside]+HALF,0,1)*0+np.clip(HALF+0.5-d[outside],0,1)
    # 3) 같은 색 같은 굵기 바깥선
    lc=np.median(rgb[(a>0.99)&(rgb.mean(-1)<110)&(yy>500)&(yy<620)&(xx<200)],0)
    L=np.clip(HALF+0.5-d,0,1)*band
    rgb=rgb*(1-L[...,None])+lc*L[...,None]; a=np.maximum(a,L)
    Image.fromarray(np.dstack([rgb.clip(0,255),a*255]).round().astype(np.uint8)).save(f,optimize=True)
    print('ok',name,lc)
for n in ('body_upper','body_upper_wave'): fix(n)
