"""아래팔+주먹(hand_r)을 GenerateImage로 다시 만든 그림(raw/hand_r_regen.jpg, 양쪽 외곽선 있음)으로 바꿈.
옛 조각은 오른쪽 가장자리가 선 없이 잘려 있어서, 팔을 -34도 내리면 머리카락 위에 뭉개져 보였음.
코드는 초록 배경 빼기(부드러운 알파 매팅)·옛 조각 상자에 맞춘 크기 조절·배치만 함. clean_edges.py 전에 실행.
사용: python3 tools/v3/regen_hand.py [parts 폴더]"""
import sys, os, numpy as np, cv2
from PIL import Image
from scipy import ndimage
HERE=os.path.dirname(os.path.abspath(__file__))
P=sys.argv[1] if len(sys.argv)>1 else f'{HERE}/../../public/v3-demo/parts'
src=np.array(Image.open(f'{HERE}/raw/hand_r_regen.jpg').convert('RGB')).astype(np.float32)
bg=np.median(src[:20].reshape(-1,3),0)
r,g,b=src[...,0],src[...,1],src[...,2]
gness=g-np.maximum(r,b)                      # 초록 정도
bgg=bg[1]-max(bg[0],bg[2])
a=np.clip(1-(gness-10)/(bgg-10),0,1)         # 초록이면 0, 살·선이면 1, 사이는 부드럽게
A=a>0.5; lb,n=ndimage.label(A); A=lb==(np.argmax(ndimage.sum(A,lb,range(1,n+1)))+1); A=ndimage.binary_fill_holes(A)
a=np.where(cv2.dilate(A.astype(np.uint8),np.ones((5,5),np.uint8))>0,a,0); a=np.maximum(a,ndimage.binary_erosion(A,iterations=2))
# 초록 번짐 제거: 반투명 가장자리 색에서 초록 빼기
spill=np.clip(g-np.maximum(r,b),0,None); src[...,1]-=spill*(1-a)
ys,xs=np.where(a>0.5); y0,y1,x0,x1=ys.min(),ys.max()+1,xs.min(),xs.max()+1
old=np.array(Image.open(f'{P}/hand_r.png').convert('RGBA')); oa=old[...,3]>128
oy,ox=np.where(oa); Y0,Y1,X0,X1=oy.min(),oy.max()+1,ox.min(),ox.max()+1
rgba=np.dstack([np.clip(src,0,255),a*255])[y0:y1,x0:x1]
fit=cv2.resize(rgba,(X1-X0,Y1-Y0),interpolation=cv2.INTER_AREA)   # 큰 그림을 줄임(계단 없이)
out=np.zeros_like(old,dtype=np.float32); out[Y0:Y1,X0:X1]=fit
Image.fromarray(np.clip(out,0,255).round().astype(np.uint8)).save(f'{P}/hand_r.png',optimize=True)
print('hand_r ok',(X1-X0,Y1-Y0),'<-',(x1-x0,y1-y0))
