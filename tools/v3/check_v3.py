"""v3 자동 검사: 실루엣 IoU·구멍, 관절 겹침 px, 관절 색 차이(ΔE), 팔레트 ΔE, 치마 단 > 반바지 단. 400% 확대 시트도 만든다.
사용: python3 tools/v3/check_v3.py public/v3-demo out_dir  (raw/canon.jpg 은 tools/v3/raw 또는 --raw)"""
import json, sys, os
import numpy as np, cv2
from PIL import Image
from scipy import ndimage
D=sys.argv[1]; OUT=sys.argv[2]; os.makedirs(OUT,exist_ok=True)
sk=json.load(open(f'{D}/skeleton.json')); W,H=sk['skeleton']['width'],sk['skeleton']['height']
skin=sk['skins'][0]['attachments']
def lab(rgb): return cv2.cvtColor((rgb[None]/255).astype(np.float32),cv2.COLOR_RGB2LAB)[0]
def layer(name_slot, att):
    a=np.zeros((H,W,4),np.uint8); im=np.array(Image.open(f"{D}/{att['path']}").convert('RGBA'))
    a[att['y']:att['y']+att['height'],att['x']:att['x']+att['width']]=im; return a
def compose(outfit, hair=True):
    c=np.zeros((H,W,4),np.float32); fit=sk['outfits'].get(outfit) if outfit else None
    for s in sk['slots']:
        n=s.get('attachment')
        if s['name'] in ('top','bottom','eyes') or s['name'].startswith(('socks','shoes','sleeve')): n=fit.get(s['name']) if fit else None
        if not n or (not hair and s['name'].startswith('hair')): continue
        L=layer(s['name'],skin[s['name']][n]).astype(np.float32); a=L[...,3:]/255
        c[...,:3]=L[...,:3]*a+c[...,:3]*(1-a); c[...,3:]=a*255+c[...,3:]*(1-a)
    return c
res={}
body=compose(None, hair=False); A=body[...,3]>128  # 캐논은 대머리 → 머리카락 빼고 비교; A=body[...,3]>128
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rmbg import rmbg
ref=rmbg(sys.argv[3]) if len(sys.argv)>3 else None  # 캔버스 원본 jpg(배경 있는 그대로)
if ref is not None:
    R=ref[...,3]>128; res['silhouette_iou']=round(float((A&R).sum()/(A|R).sum()),4)
holes=ndimage.binary_fill_holes(A)&~A; lb,n=ndimage.label(holes); res['holes_px']=int(holes.sum()); res['holes']=int(n)
# 관절 겹침: 부모·자식 조각이 둘 다 덮는 폭(관절 축 방향 최대 두께)
ov={}
bones={b['name']:b for b in sk['bones']}
base={s['bone']:layer(s['name'],skin[s['name']][s['attachment']]) for s in sk['slots'] if s.get('attachment') and s['name']==s['bone']}
dEs=[]
for n,b in bones.items():
    p=b.get('parent')
    if p not in base or n not in base: continue
    m=(base[n][...,3]>128)&(base[p][...,3]>128)
    if not m.any(): continue
    t=ndimage.distance_transform_edt(m).max()*2; ov[f'{p}>{n}']=round(float(t),1)
    # 겹친 곳에서 두 조각 색 차이(같은 원본에서 잘랐으면 0 에 가까움)
    la,lb2=lab(base[n][m][:,:3].astype(np.float32)),lab(base[p][m][:,:3].astype(np.float32))
    dEs.append(float(np.median(np.linalg.norm(la-lb2,axis=1))))
res['joint_overlap_px']=ov
res['joint_overlap_ok_8_12']=all(8<=v<=12 for k,v in ov.items() if not k.startswith('pelvis>thigh'))  # 골반>허벅지는 반바지가 덮어서 일부러 넓음
res['joint_dE_median_max']=round(max(dEs),2)
# 팔레트 ΔE(스타일 가이드 HEX 대비): 주요 색이 가이드 팔레트에서 얼마나 먼가
PAL={'outline':'6E3D5B','skin':'FFEADD','skin_shade':'F6CDBF','hair':'F4A6C4','hair_shade':'E07FA6','eye':'C2457A','top':'FCE38A','skirt':'7FAAD6','sock':'FFFFFF','shoe':'D63C44'}
pl=lab(np.array([[int(h[i:i+2],16) for i in (0,2,4)] for h in PAL.values()],np.float32))
dress=compose('basic'); M=dress[...,3]>250; px=lab(dress[M][::37,:3])
d=np.linalg.norm(px[:,None]-pl[None],axis=2).min(1); res['palette_dE_p50']=round(float(np.median(d)),2); res['palette_dE_p90']=round(float(np.percentile(d,90)),2)
# 치마 단 vs 반바지 단(가장 아래 y)
def bottom(att): im=np.array(Image.open(f"{D}/{att['path']}"))[...,3]; return att['y']+int(np.where(im.any(1))[0].max())
sk_b=bottom(skin['bottom'][sk['outfits']['basic']['bottom']])
pel=layer('pelvis',skin['pelvis']['pelvis']); pm=pel[...,3]>128
# 반바지 = 골반 조각 안의 흰/밝은 옷 색(피부 아님)
lp=pel[...,:3].astype(int); short=pm&(lp.min(-1)>236)&(np.abs(lp[...,0]-lp[...,2])<14)
res['skirt_hem_y']=sk_b; res['shorts_hem_y']=int(np.where(short.any(1))[0].max()); res['skirt_covers_shorts']=sk_b>res['shorts_hem_y']
json.dump(res,open(f'{OUT}/checks.json','w'),indent=1,ensure_ascii=False); print(json.dumps(res,ensure_ascii=False))
# 400% 확대 시트(관절·단 부분)
crops=[('어깨 L',(250,330)),('팔꿈치 L',(210,513)),('손목 L',(148,626)),('목',(359,330)),('골반',(359,700)),('무릎 R',(425,943)),('발목 R',(448,1146)),('치마 단',(300,795))]
bg=np.full((H,W,3),[253,238,246],np.float32); a=dress[...,3:]/255; img=(dress[...,:3]*a+bg*(1-a)).astype(np.uint8)
tiles=[]
for nm,(x,y) in crops:
    c=img[max(0,y-30):y+30,max(0,x-30):x+30]; c=cv2.resize(c,(240,240),interpolation=cv2.INTER_NEAREST); tiles.append(c)
sheet=np.vstack([np.hstack(tiles[:4]),np.hstack(tiles[4:])]); Image.fromarray(sheet).save(f'{OUT}/crops400.png')
