import numpy as np;from PIL import Image
from scipy.ndimage import binary_dilation
a=np.asarray(Image.open('/workspace/siha-v4/rebuild/body_F_c13.jpg').convert('RGB')).astype(float)
r,g,b=a[...,0],a[...,1],a[...,2]
gd=g-np.maximum(r,b);al=np.clip(1-(gd-20)/60,0,1)
bg=al<0.5
near=binary_dilation(bg,iterations=3)&~bg
lum=a.min(2)
rim=near&(lum>150)            # 외곽선 바깥 밝은 테 = 지우기
al[rim]=0
# 반투명 경계: 남은 밝은 섞임도 지움
half=near&(lum>110)&(gd>-10); al[half]=np.minimum(al[half],0.0)
a[...,1]=np.minimum(g,np.maximum(r,b))
edge=binary_dilation(bg,iterations=3)&~bg&(a.max(2)<140)
m=a.min(2)[edge]*0.6
for c in range(3): a[...,c][edge]=m  # 외곽선 쪽 초록 번짐 → 무채색 어두운 값
out=np.dstack([a,al*255]).astype(np.uint8);Image.fromarray(out,'RGBA').save('c13_key.png')
dk=Image.new('RGBA',(720,1280),(40,40,40,255));dk.alpha_composite(Image.fromarray(out,'RGBA'))
S=4
for n,(x,y,w,h) in {'hR':(462,625,88,125),'hair':(380,230,120,120),'arm':(200,330,120,180)}.items():
  dk.crop((x,y,x+w,y+h)).resize((w*S,h*S),Image.NEAREST).save(f'k13b_{n}.png')
