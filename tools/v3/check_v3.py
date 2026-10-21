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
        if s['name']=='arm_up_r': continue
        if not n or (not hair and s['name'].startswith('hair')): continue
        L=layer(s['name'],skin[s['name']][n]).astype(np.float32); a=L[...,3:]/255
        c[...,:3]=L[...,:3]*a+c[...,:3]*(1-a); c[...,3:]=a*255+c[...,3:]*(1-a)
    return c
res={}
body=compose(None, hair=False); A=body[...,3]>128  # 캐논은 대머리 → 머리카락 빼고 비교; A=body[...,3]>128
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rmbg import rmbg
ref=(np.array(Image.open(sys.argv[3]).convert('RGBA')) if sys.argv[3].endswith('.png') else rmbg(sys.argv[3])) if len(sys.argv)>3 else None  # 캔버스 원본 jpg(배경 있는 그대로)
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
    if n.startswith('hand') or n=='arm_up_r': continue  # 손은 크기를 줄여서(0.88) 겹친 곳 그림이 다름 → 색 비교 제외
    la,lb2=lab(base[n][m][:,:3].astype(np.float32)),lab(base[p][m][:,:3].astype(np.float32))
    dEs.append(float(np.median(np.linalg.norm(la-lb2,axis=1))))
res['joint_overlap_px']=ov
res['joint_overlap_ok_8_12']=all(v>=8 for k,v in ov.items() if not k.endswith('arm_up_r'))  # 둥근 관절 덮개 때문에 8px 이상(넓을수록 꺾임 없음)  # 골반>허벅지는 반바지가 덮어서 일부러 넓음
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

# 선 검사: 조각 바깥 테두리(2px) 중 진한 선(#6E3D5B 계열) 비율 — 팔다리도 얼굴만큼 선이 있어야 함
OUTL=lab(np.array([[110,61,91]],np.float32))[0]
line={}
for s_ in sk['slots']:
    n_=s_.get('attachment')
    if not n_ or s_['name'] in ('eyes','arm_up_r') or s_['name'].startswith('hair'): continue
    im=np.array(Image.open(f"{D}/{skin[s_['name']][n_]['path']}").convert('RGBA'))
    al=im[...,3]>128; ring=al&~ndimage.binary_erosion(al,iterations=3)
    outer=ndimage.binary_dilation(~al,iterations=1)&ring   # 실루엣 바깥쪽 테두리만
    dark=(im[...,:3].astype(int).sum(-1)<430)
    line[s_['name']]=round(float((dark&ring).sum()/max(outer.sum(),1)),2)
res['outline_ratio']=line
# 비율 검사: 캐논(cand2)과 지금 맨몸 실루엣의 팔다리 폭(가운데에서 뼈에 수직)과 길이
if len(sys.argv)>4:
    CAN=rmbg(sys.argv[4])[...,3]>128; ME=compose(None,hair=False)[...,3]>128
    def width(M,a,b):
        a=np.array(a,float); b=np.array(b,float); m=(a+b)/2; d=(b-a)/np.linalg.norm(b-a); nrm=np.array([-d[1],d[0]]); w=0
        for t in range(-80,81):
            x,y=(m+nrm*t).round().astype(int)
            if 0<=x<W and 0<=y<H and M[y,x]: w+=1
        return w
    pr={}
    for bn in ('upperarm_l','forearm_l','thigh_l','shin_l','upperarm_r','forearm_r','thigh_r','shin_r'):
        b_=bones[bn]; kid=[k for k in sk['bones'] if k.get('parent')==bn][0]['rest']
        pr[bn]=round(width(ME,(b_['rest']['x'],b_['rest']['y']),(kid['x'],kid['y']))/max(width(CAN,(b_['rest']['x'],b_['rest']['y']),(kid['x'],kid['y'])),1),3)
    ys=np.where(ME.any(1))[0]; yc=np.where(CAN.any(1))[0]
    res['limb_width_ratio_vs_canon']=pr; res['height_ratio_vs_canon']=round((ys.max()-ys.min())/(yc.max()-yc.min()),3)
    res['proportion_ok']=bool(all(0.95<=v<=1.08 for v in pr.values()) and 0.98<=res['height_ratio_vs_canon']<=1.02)
# 흰 테두리 검사: 치마·소매 조각 가장자리 2px 안에 밝은(흰) 픽셀 비율
fr={}
for sl in ('bottom','sleeve_l','sleeve_r','top'):
    im=np.array(Image.open(f"{D}/{skin[sl][sk['outfits']['basic'][sl]]['path']}").convert('RGBA')).astype(int)
    al=im[...,3]>40; ring=al&~ndimage.binary_erosion(al,iterations=2)
    fr[sl]=round(float(((im[...,:3].min(-1)>235)&ring).sum()/max(ring.sum(),1)),4)
res['fringe_white_ratio']=fr; res['fringe_ok']=max(fr.values())<0.01
# ── 손 흔들기 프레임 검사: 모든 프레임을 그려 이음새(옷 밑 흰 민소매가 드러남 + 구멍)를 센다 ──
def world(pose):
    out={}
    for bn in sk['bones']:
        p=pose.get(bn['name'],{}); jx,jy=bn['rest']['x'],bn['rest']['y']; r=np.radians(p.get('rotate',0)); c,s_=np.cos(r),np.sin(r)
        M=np.array([[c,-s_,jx-c*jx+s_*jy],[s_,c,jy-s_*jx-c*jy],[0,0,1]])
        out[bn['name']]=out[bn['parent']]@M if bn.get('parent') else M
    return out
def keys(k,t):
    if t<=k[0]['time']: return k[0]['value']
    for a,b2 in zip(k,k[1:]):
        if t<=b2['time']: u=(t-a['time'])/(b2['time']-a['time']); u=0.5-np.cos(u*np.pi)/2; return a['value']+(b2['value']-a['value'])*u
    return k[-1]['value']
LAYERS={}
SW=sk['animations']['wave'].get('swap')
def render(pose, mark_under=False, hair=True, up=False):
    Wd=world(pose); c=np.zeros((H,W,4),np.float32); fit=sk['outfits']['basic']
    for s in sk['slots']:
        if SW and up and s['name'] in SW['hide']: continue
        if SW and not up and s['name'] in SW['show']: continue
        n=fit.get('arm_up_r',s.get('attachment')) if s['name']=='arm_up_r' else s.get('attachment')
        if s['name'] in ('top','bottom','eyes') or s['name'].startswith(('socks','shoes','sleeve')): n=fit.get(s['name'])
        if not n or (not hair and s['name'].startswith('hair')): continue
        key=(s['name'],n)
        if key not in LAYERS: LAYERS[key]=layer(s['name'],skin[s['name']][n])
        L=LAYERS[key].astype(np.float32).copy()
        if mark_under and s['name'] in ('chest','neck','upperarm_l','upperarm_r'):
            u=(L[...,:3].min(-1)>240)&(np.ptp(L[...,:3],axis=-1)<8)&(L[...,3]>128); L[u,:3]=[255,0,255]
        M=Wd[s['bone']][:2]; L[...,:3]*=L[...,3:]/255  # 미리 곱한 알파로 돌려야 가장자리에 검은 줄이 안 생김(캔버스와 같음)
        L=cv2.warpAffine(L,M,(W,H),flags=cv2.INTER_LINEAR)
        a=L[...,3:]/255; c[...,:3]=L[...,:3]+c[...,:3]*(1-a); c[...,3:]=a*255+c[...,3:]*(1-a)
    return c
BODY=ndimage.binary_dilation(A,iterations=0) if ref is None else (ref[...,3]>128)  # 머리카락 사이 틈은 빼고 몸 안 구멍만
PAD=sk['skeleton'].get('stagePad',0)
fit_b=sk['outfits']['basic']
wv=sk['animations']['wave']; frames=[]; worst=0
for t in np.linspace(0,wv['period'],25):
    pose={bn:{'rotate':keys(tl['rotate'],t)} for bn,tl in wv['bones'].items()}
    up=bool(SW) and SW['on']<=t<SW['off']
    ch=render(pose,True,up=up)  # 드러난 민소매는 머리카락까지 그린 뒤(머리카락에 가려지면 안 보임)
    mag=(np.abs(ch[...,0]-255)<40)&(ch[...,1]<90)&(np.abs(ch[...,2]-255)<40)&(ch[...,3]>128)
    c=render(pose,True,hair=False,up=up); A2=c[...,3]>128  # 구멍은 머리카락 빼고(머리카락 틈은 이음새 아님)
    # 손(손끝)이 무대 밖으로 나가면 안 됨
    if up:
        aa=skin['arm_up_r'][fit_b['arm_up_r']]; hb=world(pose)['arm_up_r']
        tips=[(hb@np.array([x,y,1]))[:2] for x,y in ((aa['x'],aa['y']),(aa['x']+aa['width'],aa['y']),(aa['x']+aa['width'],aa['y']+aa['height']))]
    else:
        hb=world(pose)['hand_r']; tips=[(hb@np.array([x,y,1]))[:2] for x,y in ((634,716),(665,745),(600,745))]
    res.setdefault('wave_hand_out',0); res['wave_hand_out']+=int(any(p[0]<-PAD or p[0]>W+PAD or p[1]<0 or p[1]>H for p in tips))
    hole=ndimage.binary_fill_holes(A2)&~A2
    hole=hole&~ndimage.binary_opening(hole,iterations=3)  # 이음새 = 가는 틈(두께 ≤6px). 팔과 몸 사이 넓은 빈 곳은 이음새 아님
    seam=int(mag.sum()+hole[:650].sum()); worst=max(worst,seam); frames.append((t,seam,render(pose,up=up)))
base=frames[0][1]; res['wave_frames']=len(frames); res['wave_seam_rest_px']=base; res['wave_seam_px_max']=worst; res['wave_seam_extra_px_max']=worst-base; res['wave_seam_ok']=worst-base<=6 and base<=10 and res['wave_hand_out']==0  # 쉬는 자세보다 더 벌어진 px
json.dump(res,open(f'{OUT}/checks.json','w'),indent=1,ensure_ascii=False,default=lambda o: o.item() if hasattr(o,'item') else str(o)); print('wave seam max',worst)
# 400% 시트에 흔들기 프레임(오른쪽 어깨 둘레) 추가 — 25 프레임 전부
tiles=[]
for t,seam,c in frames:
    Wd=world({bn:{'rotate':keys(tl['rotate'],t)} for bn,tl in wv['bones'].items()})
    a=c[...,3:]/255; im=(c[...,:3]*a+bg*(1-a)).astype(np.uint8); x,y=470,420
    cr=im[y-60:y+60,x-60:x+60]; cr=cv2.resize(cr,(360,360),interpolation=cv2.INTER_NEAREST)
    cv2.putText(cr,f't={t:.2f} seam={seam}',(6,22),cv2.FONT_HERSHEY_SIMPLEX,0.6,(110,61,91),2); tiles.append(cr)
while len(tiles)%5: tiles.append(np.full_like(tiles[0],255))
wsheet=np.vstack([np.hstack(tiles[i:i+5]) for i in range(0,len(tiles),5)])
s0=np.array(Image.open(f'{OUT}/crops400.png'));pad=np.full((s0.shape[0],wsheet.shape[1]-s0.shape[1],3),255,np.uint8) if wsheet.shape[1]>s0.shape[1] else None
top=np.hstack([s0,pad]) if pad is not None else s0
Image.fromarray(np.vstack([top,wsheet])).save(f'{OUT}/crops400.png')
