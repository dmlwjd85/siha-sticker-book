# 옷 레이어: 생성된 옷 그림에서 옷 영역만 마스크로 남김(지우기·마스크만). 몸은 c14 그대로.
import sys,numpy as np;from PIL import Image
from scipy.ndimage import binary_dilation,binary_fill_holes,binary_opening,label
name,src,dx,dy,sc=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),float(sys.argv[5])
B=np.asarray(Image.open('body_F_c27.jpg').convert('RGB')).astype(int)
im=Image.open(src).convert('RGB')
if sc!=1: im=im.resize((round(720*sc),round(1280*sc)),Image.LANCZOS)
D=np.zeros((1280,720,3),int)+[50,180,50]
c=Image.new('RGB',(720,1280),(50,180,50));c.paste(im,(dx,dy));D=np.asarray(c).astype(int)
r,g,b=D[...,0],D[...,1],D[...,2]
import os
lo=int(os.environ.get('YMIN','300'));hi=int(os.environ.get('YMAX','1150'))
yy=np.arange(1280)[:,None]
band=(yy>lo)&(yy<hi)
hue=eval(os.environ.get('HUE','(r-g>30)&(b>g-5)&(r>170)'))
white=(D.min(2)>195)&((D.max(2)-D.min(2))<30)
seed=band&(hue|(white&binary_dilation(hue,iterations=10)))
seed=binary_opening(seed,iterations=2)
lab,n=label(seed);sz=np.bincount(lab.ravel());sz[0]=0
keep=np.isin(lab,np.nonzero(sz>int(os.environ.get('MINSZ','3000')))[0])     # 큰 덩어리(옷)만
near_=binary_dilation(keep,iterations=8)
small=np.isin(lab,[i for i in np.nonzero(sz>40)[0] if near_[lab==i].any()])  # 선으로 떨어진 소매단·밑단 띠
m=binary_fill_holes(keep|small)
dark=(D.max(2)<200)&((D.max(2)-D.min(2))<60)&~((g-np.maximum(r,b))>20)
m=m|(binary_dilation(m,iterations=6)&dark)     # 옷 외곽선 포함
m=binary_fill_holes(m)
m=m|(binary_dilation(m,iterations=int(os.environ.get("GROW","3")))&((D.min(2)<150)|hue)&~((g-np.maximum(r,b))>20))  # 가장자리 선(어두운 픽셀)·옷 색만 더 포함
m=m&~eval(os.environ.get('EXCL','np.zeros_like(m)'))  # 피부색(주황 그림자) 제외 마스크
gd=g-np.maximum(r,b);D=D.copy();D[...,1]=np.minimum(g,np.maximum(r,b));al=np.clip(1-(gd-20)/60,0,1)*m
out=np.dstack([D,al*255]).astype(np.uint8)
Image.fromarray(out,'RGBA').save(f'/workspace/ssb/public/v4c-demo/src/outfit/o_{name}.png')
bk=Image.open('/tmp/v4c/c13_key.png') if False else None
# c14 키 위에 합성
bb=np.asarray(Image.open('body_F_c27.jpg').convert('RGB')).astype(float)
gdb=bb[...,1]-np.maximum(bb[...,0],bb[...,2]);ab=np.clip(1-(gdb-20)/60,0,1)
bb[...,1]=np.minimum(bb[...,1],np.maximum(bb[...,0],bb[...,2]))
base=Image.new('RGBA',(720,1280),(40,40,40,255));base.alpha_composite(Image.fromarray(np.dstack([bb,ab*255]).astype(np.uint8),'RGBA'))
base.alpha_composite(Image.fromarray(out,'RGBA'));base.save(f'/workspace/ssb/public/v4c-demo/src/outfit/oc_{name}.png')
print('mask px',m.sum())
