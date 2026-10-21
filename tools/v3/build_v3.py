"""siha v3 데모 파이프라인: GenerateImage 원본(raw/*.jpg) → 배경 제거·정렬·뼈별 자르기·검사 → public/v3-demo/
코드는 그림을 그리지 않는다: 배경 제거, 정렬(ECC), 자르기(뼈 영역 + 관절 겹침), 검사만 한다."""
import json, os, sys, math
import numpy as np, cv2
from PIL import Image
from scipy import ndimage
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
from rmbg import rmbg
import argparse
ap=argparse.ArgumentParser(description='v3 조각 파이프라인')
ap.add_argument('raw',nargs='?',default=os.path.join(HERE,'raw')); ap.add_argument('out',nargs='?',default=os.path.join(HERE,'out'))
ap.add_argument('--outfit',action='append',metavar='이름=파일.jpg',help='옷 한 벌(여러 번 가능). 기본: basic=outfit.jpg')
ap.add_argument('--config',help='JSON: {"outfits": {"이름": "파일.jpg", ...}}')
args=ap.parse_args(); RAW=args.raw; OUT=args.out
OUTFITS={}
if args.config: OUTFITS.update(json.load(open(args.config)).get('outfits',{}))
for o in args.outfit or []: k,v=o.split('=',1); OUTFITS[k]=v
if not OUTFITS: OUTFITS={'basic':'outfit.jpg'}
import shutil; shutil.rmtree(f'{OUT}/parts',ignore_errors=True); os.makedirs(f'{OUT}/parts',exist_ok=True)
OVERLAP=6   # 조각마다 5px 씩 → 관절 겹침 합 ≈10px (8~12)
def L(n): return np.array(Image.open(n if os.path.isabs(n) else f'{RAW}/{n if n.endswith((".jpg",".png")) else n+".jpg"}').convert('RGB')).astype(np.float32)

# 뼈: 이름, 부모, 시작점(관절), 끝점 — 캔버스(720x1280) 좌표, y 아래로
BONES=[('root',None,(359,711),(359,711)),
 ('pelvis','root',(359,711),(359,591)),('chest','pelvis',(359,591),(359,361)),('neck','chest',(359,351),(359,296)),('head','neck',(359,301),(359,101)),
 ('upperarm_l','chest',(278,361),(210,513)),('forearm_l','upperarm_l',(210,513),(148,626)),('hand_l','forearm_l',(148,626),(103,716)),
 ('upperarm_r','chest',(442,361),(515,513)),('forearm_r','upperarm_r',(515,513),(578,626)),('hand_r','forearm_r',(578,626),(634,716)),
 ('thigh_l','pelvis',(301,694),(284,943)),('shin_l','thigh_l',(284,943),(272,1146)),('foot_l','shin_l',(272,1146),(264,1211)),
 ('thigh_r','pelvis',(419,694),(425,943)),('shin_r','thigh_r',(425,943),(448,1146)),('foot_r','shin_r',(448,1146),(454,1211))]
B={b[0]:b for b in BONES}
DRAW=['hair_back','thigh_l','thigh_r','shin_l','shin_r','foot_l','foot_r','pelvis','chest','neck','head','eyes',
      'upperarm_l','forearm_l','hand_l','upperarm_r','forearm_r','hand_r','hair_front']

def align(src, ref):
    """ECC 아핀 정렬(같은 구도로 생성한 이미지의 미세한 어긋남 보정)."""
    g1=cv2.cvtColor(ref.astype(np.uint8),cv2.COLOR_RGB2GRAY).astype(np.float32); g2=cv2.cvtColor(src.astype(np.uint8),cv2.COLOR_RGB2GRAY).astype(np.float32)
    W=np.eye(2,3,dtype=np.float32)
    try: _,W=cv2.findTransformECC(g1,g2,W,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,200,1e-6),None,5)
    except cv2.error: pass
    return cv2.warpAffine(src,W,(ref.shape[1],ref.shape[0]),flags=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE), W

def segdist(P, a, b):
    a=np.array(a,float); b=np.array(b,float); d=b-a; L2=max(d@d,1e-6)
    t=np.clip(((P-a)@d)/L2,0,1); q=a+t[...,None]*d; return np.hypot(*(P-q).transpose(2,0,1))

def defringe(a, px=3):
    """가장자리 px 안의 밝은(배경이 섞인) 색을 안쪽 색으로 바꾸고, 바깥 1px 은 반투명으로."""
    al=a[...,3]>8; inner=ndimage.binary_erosion(al,iterations=px)
    if not inner.any(): return a
    _,(iy,ix)=ndimage.distance_transform_edt(~inner,return_indices=True)
    ring=al&~inner; src=a[iy,ix,:3].astype(int); cur=a[...,:3].astype(int)
    light=(cur.sum(-1)>src.sum(-1)+30)&ring
    a[...,:3][light]=src[light].astype(np.uint8)
    edge=al&~ndimage.binary_erosion(al,iterations=1); a[...,3][edge]=(a[...,3][edge]*0.6).astype(np.uint8)
    return a
def save_part(name, rgba, mask, bone, fringe=False):
    m=mask.astype(np.float32)
    a=rgba.copy(); a[...,3]=(a[...,3].astype(np.float32)*m).astype(np.uint8)
    if fringe: a=defringe(a)
    ys,xs=np.where(a[...,3]>0)
    if not len(ys): return None
    x0,y0,x1,y1=xs.min(),ys.min(),xs.max()+1,ys.max()+1
    Image.fromarray(a[y0:y1,x0:x1]).save(f'{OUT}/parts/{name}.png',optimize=True)
    return {'name':name,'bone':bone,'x':int(x0),'y':int(y0),'w':int(x1-x0),'h':int(y1-y0)}

canon=L('canon'); CA=rmbg(f'{RAW}/canon.jpg'); H,W=CA.shape[:2]
alpha=CA[...,3]>8
yy,xx=np.mgrid[0:H,0:W]; P=np.dstack([xx,yy]).astype(float)
limb=[b for b in BONES if b[0]!='root']
D=np.stack([segdist(P,b[2],b[3]) for b in limb]); own=np.argmin(D,0)
names=[b[0] for b in limb]
# 몸통 줄: 머리/목/가슴/골반은 세로 띠로(가운데 축) — 거리 비교 대신 y 로
def bandmask(n):
    y0={'head':0,'neck':300,'chest':352,'pelvis':590}[n]; y1={'head':300,'neck':352,'chest':590,'pelvis':712}[n]
    return (yy>=y0)&(yy<y1)
core=np.isin(own,[names.index(n) for n in ('head','neck','chest','pelvis')])
atts=[]
for i,n in enumerate(names):
    reg=(own==i)&alpha
    if n in ('head','neck','chest','pelvis'): reg=core&bandmask(n)&alpha
    CAP={'upperarm':42,'forearm':30,'hand':60,'thigh':70,'shin':52,'foot':60}
    k0=n.split('_')[0]
    if k0 in CAP: reg=reg&(D[i]<CAP[k0])
    # 관절 겹침: 자기 영역에서 OVERLAP px 안쪽까지 (거리 기반 → 끝이 둥글다)
    dist=ndimage.distance_transform_edt(~reg)
    m=np.clip(OVERLAP+0.5-dist,0,1)*alpha
    if k0 in CAP: m=m*(D[i]<CAP[k0]+OVERLAP)
    if n=='pelvis': m=np.maximum(m,((own>=names.index('thigh_l'))&(yy<712+OVERLAP)&alpha).astype(float)*(yy>=590))  # 반바지 전체
    atts.append(save_part(n,CA,m,n))
# 눈 감기: 감은 눈 이미지에서 눈 둘레만(차이 영역) 오려 머리뼈에
ec,_=align(L('eyes_closed'),canon)
diff=np.abs(ec-canon).max(-1); eyezone=(yy>150)&(yy<230)&(xx>250)&(xx<470)
em=ndimage.binary_dilation((diff>28)&eyezone,iterations=6); em=ndimage.binary_closing(em,iterations=4)
em=ndimage.gaussian_filter(em.astype(float),1.2)*alpha
E=np.dstack([ec,np.full((H,W),255,np.float32)]).astype(np.uint8)
eyes=save_part('eyes_closed',E,em,'head')
# 머리카락: 머리카락 이미지에서 캔버스와 다른 분홍 영역
hr,_=align(L('hair'),canon); HA=rmbg(f'{RAW}/hair.jpg'); HA[...,:3]=hr.astype(np.uint8) if False else HA[...,:3]
ha=HA[...,3]>8
hd=np.abs(hr-canon).max(-1)
pink=(hr[...,0]-hr[...,1]>38)&(hr[...,2]-hr[...,1]>-5)
hm=ha&((~alpha)|(hd>40))&(pink|((hr.sum(-1)<420)&ndimage.binary_dilation(pink,iterations=3)))
hm=ndimage.binary_opening(hm,iterations=1); hm=ndimage.binary_closing(hm,iterations=2)
lab,n=ndimage.label(hm); sz=ndimage.sum(hm,lab,range(1,n+1)); hm=np.isin(lab,[i+1 for i,s in enumerate(sz) if s>300])
HR=np.dstack([hr,HA[...,3].astype(np.float32)]).astype(np.uint8)
front=hm&alpha&(yy<300); back=hm&~front&(~alpha|ndimage.binary_dilation(pink&ha,iterations=1))  # 몸 위에는 분홍 머리카락만(팔 바깥선 유령 방지)
armz=ndimage.binary_dilation(np.isin(own,[names.index(x) for x in ('upperarm_l','forearm_l','hand_l','upperarm_r','forearm_r','hand_r')])&alpha,iterations=5)
back=back&~(armz&~pink)  # 팔 바깥선은 머리카락이 아님
lb_,nb_=ndimage.label(back); sb_=ndimage.sum(back,lb_,range(1,nb_+1)); back=np.isin(lb_,[i+1 for i,v in enumerate(sb_) if v>150])
hf=save_part('hair_front',HR,ndimage.gaussian_filter(front.astype(float),0.6)*front.astype(float)+0*front,'head')
hb=save_part('hair_back',HR,back.astype(float),'head')
cloth=[]
def cut_outfit(oname, fname):
    # 옷: 옷 이미지에서 캔버스와 다른 영역 → 가까운 뼈 → 종류(윗옷/치마/양말/신발)
    ot,_=align(L(fname),canon); OA=rmbg(fname if os.path.isabs(fname) else f'{RAW}/{fname}'); oa=OA[...,3]>8
    od=np.abs(ot-canon).max(-1)
    cm=oa&((~alpha)|(od>34)|((od>22)&(yy>1040))); cm=ndimage.binary_opening(cm,iterations=1); cm=ndimage.binary_closing(cm,iterations=2)
    lab,n=ndimage.label(cm); sz=ndimage.sum(cm,lab,range(1,n+1)); cm=np.isin(lab,[i+1 for i,s in enumerate(sz) if s>200])
    red=(ot[...,0]-ot[...,1]>70)
    skin=(np.abs(ot-np.array([255,234,221])).max(-1)<26)|(ot.sum(-1)<330)&~red
    cm=cm&~(skin&(yy<1040)); cm=ndimage.binary_opening(cm,iterations=2)
    Dall=np.stack([segdist(P,b[2],b[3]) for b in limb]); ownc=np.argmin(Dall,0)
    OT=np.dstack([ot,OA[...,3].astype(np.float32)]).astype(np.uint8)
    kind={'chest':'top','upperarm_l':'top','upperarm_r':'top','pelvis':'bottom','thigh_l':'bottom','thigh_r':'bottom','shin_l':'socks','shin_r':'socks','foot_l':'shoes','foot_r':'shoes'}
    skirt=cm&(yy>=560)&(yy<820)&((ot[...,2]-ot[...,0])>20)        # 파란 치마는 골반뼈에 한 장
    for i,n in enumerate(names):
        k=kind.get(n)
        if not k: continue
        reg=cm&(ownc==i)&~skirt
        if k=='shoes': reg=reg&red
        if k=='socks': reg=cm&np.isin(ownc,[names.index(n),names.index(n.replace('shin','foot'))])&~red&(yy>850)
        if k=='bottom':
            if n!='pelvis': continue
            reg=skirt
        if k=='top' and n!='chest': reg=reg&(yy<520)
        if k=='top':
            if n!='chest': continue
            # 캐논의 흰 민소매가 옷 밖으로 비치지 않게: 민소매 자리(+3px)는 옷 그림(피부/옷)으로 덮는다
            tank=ndimage.binary_dilation((canon.min(-1)>228)&(np.ptp(canon,axis=-1)<18)&alpha&(yy>300)&(yy<600),iterations=3)&oa
            tops=(cm|tank)&np.isin(ownc,[names.index(x) for x in ('chest','upperarm_l','upperarm_r','neck')])&(yy<580)&(yy>330)&~skirt
            tops=ndimage.binary_opening(tops,iterations=2); lb,nn=ndimage.label(tops); ss=ndimage.sum(tops,lb,range(1,nn+1)); tops=np.isin(lb,[j+1 for j,v in enumerate(ss) if v>1500])
            reg=ndimage.binary_fill_holes(ndimage.binary_closing(tops,iterations=8)); reg=ndimage.binary_dilation(reg,iterations=3)|tank
        if reg.sum()<50: continue
        m=ndimage.binary_dilation(reg,iterations=2)&oa
        if k=='bottom':
            # 치마: 파란 천 + 바로 붙은 바깥선(어두운 색)만. 단 밑 피부·그림자 띠는 뺀다(흰 테두리 원인)
            blue=skirt; near=ndimage.binary_dilation(blue,iterations=4)&oa
            dark=ot.sum(-1)<420
            m=(blue|(near&dark))&oa
            shorts=ndimage.binary_dilation((canon.min(-1)>228)&(np.ptp(canon,axis=-1)<18)&alpha&(yy>520)&(yy<760),iterations=3)&oa
            m=ndimage.binary_fill_holes(m|shorts)  # 캐논 흰 반바지 자리는 옷 그림으로 덮는다
            m=m&~(np.isin(ownc,[names.index(x) for x in ('forearm_l','hand_l','forearm_r','hand_r')])&((xx<262)|(xx>456)))  # 몸통 밖 손·아래팔 바깥선 유령 방지
            lb,nn=ndimage.label(m); m=lb==(1+int(np.argmax(ndimage.sum(m,lb,range(1,nn+1)))))
        if k=='top':
            m=m&~(np.isin(ownc,[names.index(x) for x in ('forearm_l','hand_l','forearm_r','hand_r')])&(yy>430))  # 아래팔 바깥선 유령 방지
            # 소매 = 윗팔뼈에 가까운 + 겨드랑이(y<440) 위 / 나머지는 몸통. 몸통은 소매 쪽으로 OVERLAP 겹침
            arm={'l':names.index('upperarm_l'),'r':names.index('upperarm_r')}
            torso=m.copy()
            for side,ix in arm.items():
                sm=(m|tank)&(ownc==ix)&((yy<440)|tank)&((xx<300) if side=='l' else (xx>420))
                lb,nn=ndimage.label(sm)
                if nn>1: sm=lb==(1+int(np.argmax(ndimage.sum(sm,lb,range(1,nn+1)))))  # 부스러기 없이 소매 한 덩어리
                a=save_part(f'{oname}_sleeve_upperarm_{side}',OT,(ndimage.binary_dilation(sm,iterations=3)&(m|tank)).astype(float),f'upperarm_{side}',fringe=True); a['kind']='sleeve'; a['slot']=f'sleeve_{side}'; a['outfit']=oname; cloth.append(a)
                # 몸통 쪽 어깨 덮개(shoulder cap)는 남겨 둔다: 팔을 들어도 겨드랑이가 비지 않음
            m=torso
        a=save_part(f'{oname}_{k}_{n}',OT,m.astype(float),n,fringe=True); a['kind']=k; a['outfit']=oname
        a['slot']={'top':'top','bottom':'bottom'}.get(k) or f"{k}_{n[-1]}"; cloth.append(a)
for on,fn in OUTFITS.items(): cut_outfit(on,fn)
# 장식: 두 덩어리(리본, 별 핀)
AC=rmbg(f'{RAW}/accs.jpg'); lab,n=ndimage.label(AC[...,3]>128); sz=ndimage.sum(AC[...,3]>128,lab,range(1,n+1))
big=sorted([i+1 for i,s in enumerate(sz) if s>2000],key=lambda i:np.where(lab==i)[1].mean())
accs=[]
for nm,i in zip(['acc_ribbon','acc_star'],big):
    m=ndimage.binary_dilation(lab==i,iterations=3)
    a=save_part(nm,AC,m.astype(float),None); accs.append(a)
json.dump({'size':[W,H],'bones':BONES,'atts':atts,'eyes':eyes,'hair':[hb,hf],'cloth':cloth,'accs':accs},open(f'{OUT}/build.json','w'),indent=1)
# 검사용 겹침 미리보기
col=np.zeros((H,W,3),np.uint8); rng=np.random.default_rng(3); pal=rng.integers(60,255,(len(names),3))
col[alpha]=pal[own[alpha]]; Image.fromarray(col).save(f'{OUT}/_seg.png')
print('ok parts',len(atts),'cloth',[c['name'] for c in cloth],'accs',len(accs),'hair',[x and x['w'] for x in (hb,hf)])
