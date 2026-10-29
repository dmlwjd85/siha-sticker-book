"""부품 해상도 2배 업스케일(배치·검수용 코드). 새로 그리지 않고, 무료 오픈소스 Real-ESRGAN(anime_6B, BSD-3)으로
GenerateImage 원화 부품을 4배로 키운 뒤 2배 크기로 줄여 저장한다. skeleton.json의 width/height(무대 좌표)는 그대로라
리그·좌표는 바뀌지 않고 화면에서 더 선명하게 그려진다.
사용: python3 tools/v3/upscale_parts.py [원본 parts 폴더] [출력 parts 폴더] [모델 .pth]
필요: pip install torch(cpu) torchvision spandrel, 모델 https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"""
import sys, os, numpy as np, cv2, torch
from PIL import Image
from scipy import ndimage
import spandrel
SRC,DST=sys.argv[1],sys.argv[2]; MODEL=sys.argv[3] if len(sys.argv)>3 else '/workspace/esr/RealESRGAN_x4plus_anime_6B.pth'
os.makedirs(DST,exist_ok=True); torch.set_num_threads(os.cpu_count())
net=spandrel.ModelLoader().load_from_file(MODEL).model.eval()
def sr(img,T=192,O=16):   # img float 0..1 HxWx3 → 4배 (겹치는 타일)
    h,w=img.shape[:2]; out=np.zeros((h*4,w*4,3),np.float32); wt=np.zeros((h*4,w*4,1),np.float32)
    for y in range(0,h,T-2*O):
        for x in range(0,w,T-2*O):
            y0,x0=max(0,min(y,h-T)),max(0,min(x,w-T)); t=img[y0:y0+T,x0:x0+T]
            with torch.no_grad(): r=net(torch.from_numpy(t).permute(2,0,1)[None])[0].permute(1,2,0).clamp(0,1).numpy()
            th,tw=r.shape[:2]; ramp=lambda n: np.clip(np.minimum(np.arange(n)+1,n-np.arange(n))/(O*4),0.05,1)
            m=(ramp(th)[:,None]*ramp(tw)[None,:])[...,None]
            out[y0*4:y0*4+th,x0*4:x0*4+tw]+=r*m; wt[y0*4:y0*4+th,x0*4:x0*4+tw]+=m
    return out/np.maximum(wt,1e-6)
def bleed(rgb,a):   # 투명한 곳에 가장자리 색을 번져 채움(업스케일할 때 바깥이 검게/희게 번지지 않게)
    m=a>0.95
    if m.all() or not m.any(): return rgb
    _,(iy,ix)=ndimage.distance_transform_edt(~m,return_indices=True); return rgb[iy,ix]
for n in sorted(os.listdir(SRC)):
    if not n.endswith('.png') or (os.environ.get('SKIP_DONE') and os.path.exists(f'{DST}/{n}')): continue
    im=np.array(Image.open(f'{SRC}/{n}').convert('RGBA')).astype(np.float32)/255
    h,w=im.shape[:2]; P=8
    rgb=np.pad(bleed(im[...,:3],im[...,3]),((P,P),(P,P),(0,0)),mode='edge'); a=np.pad(im[...,3],P)
    R=sr(rgb); A=sr(np.repeat(a[...,None],3,-1)).mean(-1)
    R=R[P*4:-P*4,P*4:-P*4]; A=A[P*4:-P*4,P*4:-P*4]
    R=cv2.resize(R,(w*2,h*2),interpolation=cv2.INTER_AREA); A=cv2.resize(A,(w*2,h*2),interpolation=cv2.INTER_AREA)
    A0=cv2.resize(im[...,3],(w*2,h*2),interpolation=cv2.INTER_LINEAR)
    A=np.where(A0<0.004,0,np.clip(A,0,1)); A=np.minimum(A,np.clip((A0-0.1)/0.5,0,1))   # 원래 실루엣 밖으로 새지 않게
    # 바깥 테두리 2~3px의 회색 끼(원화 JPG 가장자리 잔색)를 안쪽 외곽선 색으로 맞춤
    inside=A>0.5; dep=ndimage.distance_transform_edt(inside)
    lum=R.mean(-1); lineish=(R[...,0]-R[...,1]>0.12)&(lum<0.5)
    src=(dep>=2)&(dep<14)&lineish
    if src.any():
        _,(iy,ix)=ndimage.distance_transform_edt(~src,return_indices=True)
        ring=(A>0)&(dep<8)&~lineish&(lum<0.6); R[ring]=R[iy,ix][ring]
    Image.fromarray((np.dstack([R,A])*255).round().clip(0,255).astype(np.uint8)).save(f'{DST}/{n}',optimize=True)
    print(n,(w,h),'->',(w*2,h*2),flush=True)
