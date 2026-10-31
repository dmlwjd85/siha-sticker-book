# 4단계: Real-ESRGAN 4x(anime_6B) → 0.5배 LANCZOS(=2배) → 초록 키·스필 제거 → 부위·옷 레이어 → skeleton.json(v4b 형식)
# 지우기·마스크·처리값만 사용. 옷 알파는 720 원본에서 만든 마스크(outfit27.py)를 2배 BILINEAR.
import json,numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import binary_dilation as bd, distance_transform_edt
RAMP=3;S=2;W,H=1440,2560;R='/workspace/siha-v4/rebuild/';P='/workspace/ssb/public/v4c-demo/'
def key(f):
    a=np.asarray(Image.open(f).convert('RGB')).astype(float);r,g,b=a[...,0],a[...,1],a[...,2]
    al=np.clip(1-(g-np.maximum(r,b)-20)/60,0,1);rgb=a.copy();rgb[...,1]=np.minimum(g,np.maximum(r,b));return rgb,al
rgb,alpha=key(R+'x4/body_F_c27_x2.png')
bg=alpha<0.5;lum=np.asarray(Image.open(R+'x4/body_F_c27_x2.png').convert('RGB')).min(2)
rim=bg.copy()
for _ in range(6): rim=rim|(bd(rim)&(lum>150))
alpha[rim&~bg]=0
e=(bd(rim,iterations=2)&~rim)&(rgb.max(2)<140);mm=rgb.min(2)[e]*0.6
for c in range(3): rgb[...,c][e]=mm
def poly(pts):
    m=Image.new('L',(W,H),0);ImageDraw.Draw(m).polygon([(x*S,y*S) for x,y in pts],fill=255);return np.asarray(m)>0
armL=poly([(0,330),(190,330),(198,400),(262,440),(272,455),(262,500),(258,560),(240,620),(0,620)])
armR=poly([(418,470),(440,462),(530,470),(720,470),(720,900),(560,900),(460,800),(412,650),(416,560),(416,520)])
head=poly([(200,0),(720,0),(720,470),(530,470),(440,462),(418,450),(262,445),(205,385),(195,330)])&~armL
rest=~(armL|armR|head);d14=bd(rest,iterations=14)
bodyM=rest|(d14&(armL|armR|head))
ramp=lambda m:np.clip(distance_transform_edt(m)/RAMP,0,1)
cL,cR,cH=ramp(armL|bg),ramp(armR|bg),ramp(head|bg)
SL={}
def save(name,rgb,A,bone,item=None):
    A=(A*255).round().astype(np.uint8);ys,xs=np.nonzero(A>0)
    if len(xs)==0: return
    x0,y0,x1,y1=xs.min(),ys.min(),xs.max()+1,ys.max()+1
    Image.fromarray(np.dstack([rgb.clip(0,255).astype(np.uint8),A])[y0:y1,x0:x1],'RGBA').save(P+f'parts/{name}.png')
    s=dict(name=name,bone=bone,path=f'parts/{name}.png',x=int(x0),y=int(y0),width=int(x1-x0),height=int(y1-y0))
    if item: s['item']=item
    SL[name]=s
save('body',rgb,alpha*bodyM,'root');save('arm_R',rgb,alpha*armR*cR,'arm_R');save('arm_L',rgb,alpha*armL*cL,'arm_L');save('head',rgb,alpha*head*cH,'head')
OUT={'dress':('dress_c27b','d27b2'),'top':('sailor_c27e','saile'),'crop':('crop_c27e','crope')}
for it,(src,mk) in OUT.items():
    orgb,_=key(R+f'x4/{src}_x2.png')
    m=np.asarray(Image.open(P+f'src/outfit/o_{mk}.png').getchannel('A').resize((W,H),Image.BILINEAR)).astype(float)/255
    save(f'item_{it}_body',orgb,m*bodyM,'root',it);save(f'item_{it}_arm_R',orgb,m*armR*cR,'arm_R',it)
    save(f'item_{it}_arm_L',orgb,m*armL*cL,'arm_L',it);save(f'item_{it}_neck',orgb,m*head*cH,'head',it)
# 소품: 단독 생성 그림을 키잉한 레이어를 크기 조절·이동만 해서 배치
def prop(name,fn,cx,top,w,bone,item):
    im=Image.open(P+f'src/outfit/{fn}');h=round(im.height*w/im.width);im=im.resize((w,h),Image.LANCZOS)
    x0=int(cx-w/2);im.save(P+f'parts/{name}.png');SL[name]=dict(name=name,bone=bone,path=f'parts/{name}.png',x=x0,y=int(top),width=w,height=h,item=item)
prop('item_tiara','o_tiara.png',350*S,112*S,150*S,'head','tiara')
prop('item_wand','o_wand.png',600*S,640*S,80*S,'hand_R','wand')
order=['body','arm_R','arm_L','item_dress_body','item_top_body','item_crop_body','item_dress_arm_R','item_top_arm_R','item_crop_arm_R','item_wand','item_dress_arm_L','item_top_arm_L','item_crop_arm_L','head','item_dress_neck','item_top_neck','item_crop_neck','item_tiara']
sk={"skeleton":{"width":W,"height":H,"scale":2,"stagePad":160,"jointOverlap":24,"note":"v4c: c27(GenerateImage) → Real-ESRGAN anime_6B 4배 → 0.5배 LANCZOS(2배) → 초록 키·스필 제거 → 몸·머리·왼팔·오른팔 4영역(몸은 팔·머리 아래 14px 확장, 자른 면 8px 알파 램프). 옷(원피스 dress_c27b, 세일러 sailor_c27e, 크롭 crop_c27e)은 c27 참조로 생성한 그림에서 옷 영역만 마스크(outfit27.py) → 같은 4영역으로 나눠 해당 뼈에 붙임. 티아라·요술봉은 단독 생성 그림 키잉 후 크기 조절·이동만. 덧칠 없음."},
 "bones":[{"name":"root","rest":{"x":720,"y":1280}},{"name":"chest","parent":"root","rest":{"x":680,"y":960}},{"name":"head","parent":"chest","rest":{"x":680,"y":890}},{"name":"arm_L","parent":"chest","rest":{"x":480,"y":960}},{"name":"arm_R","parent":"chest","rest":{"x":860,"y":980}},{"name":"hand_L","parent":"arm_L","rest":{"x":250,"y":620}},{"name":"hand_R","parent":"arm_R","rest":{"x":1080,"y":1540}}],
 "slots":[SL[n] for n in order if n in SL],
 "items":[{"id":"dress","label":"원피스","excl":["top","crop"]},{"id":"top","label":"세일러","excl":["dress","crop"]},{"id":"crop","label":"크롭 상의","excl":["top","dress"]},{"id":"wand","label":"요술봉","excl":[]},{"id":"tiara","label":"티아라","excl":[]}],
 "animations":{"breathe":{"period":4.2,"y":[[0,0],[2.1,-3],[4.2,0]]},"wave":{"bone":"arm_L","period":1.6,"repeat":2,"angle":[[0,0],[0.4,3],[0.8,-1.5],[1.2,3],[1.6,0]],"changeBox":[0,500,700,1300]}}}
json.dump(sk,open(P+'skeleton.json','w'),ensure_ascii=False,indent=0)
print(len(sk['slots']),[s['name'] for s in sk['slots']])
