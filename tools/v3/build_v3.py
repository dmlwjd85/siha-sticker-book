"""siha v3 조각 파이프라인 (그림은 전부 GenerateImage; 코드는 배경 지우기·정렬·자르기·검사만)
사용:
  python3 build_v3.py [raw] [out] [--base 파일] [--eyes 파일] [--hair 파일] [--accs 파일]
                      [--outfit 이름=파일 ...] [--config outfits.json]
기준(캐논) = raw/canon.jpg. 다른 그림은 모두 캐논에 정렬(ECC 아핀)해서 같은 좌표로 맞춘다."""
import json, os, sys, shutil, argparse
import numpy as np, cv2
from PIL import Image
from scipy import ndimage
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
from rmbg import rmbg
ap=argparse.ArgumentParser()
ap.add_argument('raw',nargs='?',default=os.path.join(HERE,'raw')); ap.add_argument('out',nargs='?',default=os.path.join(HERE,'out'))
ap.add_argument('--base',default='body_lines_raw.jpg',help='맨몸(굵은 선) 그림')
ap.add_argument('--eyes',default='eyes_closed_lines.jpg'); ap.add_argument('--hair',default='hair_lines.jpg'); ap.add_argument('--accs',default='accs.jpg')
ap.add_argument('--hands',default='hands_sheet.jpg',help='손만 가져올 그림(손가락 모은 자연스러운 손)')
ap.add_argument('--base_wave',default='body_wave.jpg',help='맨몸 손 흔드는 자세(오른쪽 팔만 다름)')
ap.add_argument('--outfit',action='append',metavar='이름=파일 또는 이름=파일,흔들기파일'); ap.add_argument('--config')
args=ap.parse_args(); RAW,OUT=args.raw,args.out
OUTFITS={}
if args.config: OUTFITS.update(json.load(open(args.config)).get('outfits',{}))
for o in args.outfit or []: k,v=o.split('=',1); OUTFITS[k]=v
if not OUTFITS: OUTFITS={'basic':'outfit_lines.jpg,outfit_wave.jpg'}
shutil.rmtree(f'{OUT}/parts',ignore_errors=True); os.makedirs(f'{OUT}/parts'); TMP=f'{OUT}/_tmp'; os.makedirs(TMP,exist_ok=True)
W,H=720,1280; OVERLAP=6; HAND_SCALE=1.0
P_=lambda n: n if os.path.isabs(n) else f'{RAW}/{n}'

# 뼈: 이름, 부모, 시작(관절·회전축), 끝. 윗팔 회전축은 어깨 안쪽(겨드랑이 위)으로.
BONES=[('root',None,(359,711),(359,711)),
 ('pelvis','root',(359,711),(359,591)),('chest','pelvis',(359,591),(359,361)),('neck','chest',(359,351),(359,296)),('head','neck',(359,301),(359,101)),
 ('upperarm_l','chest',(290,372),(210,513)),('forearm_l','upperarm_l',(210,513),(148,626)),('hand_l','forearm_l',(148,626),(103,716)),
 ('upperarm_r','chest',(430,372),(515,513)),('forearm_r','upperarm_r',(515,513),(578,626)),('hand_r','forearm_r',(578,626),(634,716)),
 ('thigh_l','pelvis',(301,694),(284,943)),('shin_l','thigh_l',(284,943),(272,1146)),('foot_l','shin_l',(272,1146),(264,1211)),
 ('thigh_r','pelvis',(419,694),(425,943)),('shin_r','thigh_r',(425,943),(448,1146)),('foot_r','shin_r',(448,1146),(454,1211))]
# 손 흔들기 자세(그림을 갈아 끼움): 팔꿈치 회전축, 손목 쪽 끝
WAVE_ELBOW=(535,500); WAVE_HAND=(605,280); WAVE_SHOULDER=(440,392)
BONES.append(('arm_up_r','chest',WAVE_SHOULDER,WAVE_HAND))
J={b[0]:b[2] for b in BONES}

def gray(x): return cv2.cvtColor(x.astype(np.uint8),cv2.COLOR_RGB2GRAY).astype(np.float32)
REF=np.array(Image.open(P_('canon.jpg')).convert('RGB').resize((W,H))).astype(np.float32)
def load(name, ref=REF):
    """생성 그림 → 720x1280 → 배경 지우기 → 캐논에 ECC 정렬. (rgb, rgba) 반환"""
    im=Image.open(P_(name)).convert('RGB').resize((W,H),Image.LANCZOS); tp=f'{TMP}/{os.path.basename(name)}.png'; im.save(tp)
    rgb=np.array(im).astype(np.float32); rgba=rmbg(tp)
    M=np.eye(2,3,dtype=np.float32)
    try: _,M=cv2.findTransformECC(gray(ref),gray(rgb),M,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,300,1e-6),None,5)
    except cv2.error: pass
    f=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP
    rgb=cv2.warpAffine(rgb,M,(W,H),flags=f,borderMode=cv2.BORDER_REPLICATE)
    rgba=cv2.warpAffine(rgba,M,(W,H),flags=f,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
    return rgb,rgba

def segdist(P,a,b):
    a=np.array(a,float); b=np.array(b,float); d=b-a; L2=max(d@d,1e-6)
    t=np.clip(((P-a)@d)/L2,0,1); q=a+t[...,None]*d; return np.hypot(*(P-q).transpose(2,0,1))
def defringe(a, px=3, srcA=None):
    """가장자리 px 안의 밝은(배경 섞인) 색을 안쪽 색으로 바꾼다(흰 테두리 제거)."""
    al=a[...,3]>8; inner=ndimage.binary_erosion(al,iterations=px)
    if not inner.any(): return a
    _,(iy,ix)=ndimage.distance_transform_edt(~inner,return_indices=True)
    ring=al&~inner; src=a[iy,ix,:3].astype(int); cur=a[...,:3].astype(int)
    light=(cur.sum(-1)>src.sum(-1)+24)&ring
    sd=src.sum(-1)<430   # 안쪽이 진한 선이면 칠하지 말고 투명하게(선 밖 진한 점이 생기지 않게)
    a[...,:3][light&~sd]=src[light&~sd].astype(np.uint8); cutp=(srcA>200) if srcA is not None else np.zeros_like(sd)
    a[...,:3][light&sd&~cutp]=src[light&sd&~cutp].astype(np.uint8); a[...,3][light&sd&cutp]=0   # 자른 곳만 투명, 원래 가장자리는 AA 유지
    return a
def keep_big(m, min_px):
    lb,n=ndimage.label(m)
    if n==0: return m
    sz=ndimage.sum(m,lb,range(1,n+1)); return np.isin(lb,[i+1 for i,s in enumerate(sz) if s>=min_px])
def despeck(rgba, m):
    """옷 가장자리 밖으로 매달린 진한 점(선 부스러기) 제거: 5px 보다 가는 진한 돌기만 뺀다"""
    mb=m>0.5; dk=rgba[...,:3].astype(int).sum(-1)<430
    keep=ndimage.binary_opening(mb,iterations=2)|(mb&~dk)
    keep=keep_big(keep,200)
    return (m*keep) if m.dtype!=bool else (m&keep)
def clean_hem(rgba, m, band=14):
    """옷 단 안쪽의 연한 둘째 선(이중선)을 둘레 색으로 메워 바깥 진한 선 하나만 남긴다"""
    mb=m>0.5
    rgb=rgba[...,:3].copy(); med=cv2.medianBlur(rgb,9).astype(int); v=rgb.astype(int)
    dk=v.sum(-1)<430
    yl=(v[...,0]>200)&(v[...,1]>170)&(v[...,2]<190)&(v[...,0]-v[...,2]>40)
    other=~yl&~dk   # 피부·배경
    hem=dk&ndimage.binary_dilation(yl,iterations=2)&ndimage.binary_dilation(other|~mb,iterations=2)   # 옷 단 바깥 진한 선
    dk5=v.sum(-1)<470
    inner=mb&(ndimage.distance_transform_edt(~hem)<=32)&(ndimage.distance_transform_edt(~dk5)>=3)&~ndimage.binary_dilation(other,iterations=1)
    line=inner&~dk&(np.abs(v-med).sum(-1)>8)
    line=ndimage.binary_dilation(line,iterations=1)&mb&(ndimage.distance_transform_edt(~dk5)>=2)&~ndimage.binary_dilation(other,iterations=1)
    out=rgba.copy(); out[...,:3]=cv2.inpaint(rgb,line.astype(np.uint8)*255,4,cv2.INPAINT_TELEA); return out,int(line.sum())
def save_part(name, rgba, mask, bone, scale=None, ds=False):
    a=rgba.copy(); a[...,3]=(a[...,3].astype(np.float32)*np.clip(mask.astype(np.float32),0,1)).astype(np.uint8)
    a=defringe(a,srcA=rgba[...,3] if ds and name!='arm_up_r' and not name.endswith('_arm_up_r') else None)
    if ds: a[...,3]=(a[...,3]*despeck(a,a[...,3]>8)).astype(np.uint8)   # 옷: 가장자리 정리 뒤 매달린 진한 점 제거
    ys,xs=np.where(a[...,3]>0)
    if not len(ys): return None
    x0,y0,x1,y1=xs.min(),ys.min(),xs.max()+1,ys.max()+1; c=a[y0:y1,x0:x1]
    if scale:   # 크기 맞춤: 관절(scale[1])을 고정점으로 줄이기
        s,(px,py)=scale; im=Image.fromarray(c); nw,nh=max(1,round(im.width*s)),max(1,round(im.height*s))
        im=im.resize((nw,nh),Image.LANCZOS); x0=round(px-(px-x0)*s); y0=round(py-(py-y0)*s); c=np.array(im)
    Image.fromarray(c).save(f'{OUT}/parts/{name}.png',optimize=True)
    return {'name':name,'bone':bone,'x':int(x0),'y':int(y0),'w':int(c.shape[1]),'h':int(c.shape[0])}

yy,xx=np.mgrid[0:H,0:W]; P=np.dstack([xx,yy]).astype(float)
base,BA=load(args.base); alpha=BA[...,3]>128
# 손 갈아 끼우기: 새로 그린 "손가락 모은 손"을 손목 기준으로 돌려 팔 방향에 맞춘 뒤 손목 아래만 바꾼다
# (손 그림 좌표: 720x1280 기준 손목·팔뚝 점, 정렬 없이 그대로)
HAND_SRC={'hand_l':((190,672),(220,530)),'hand_r':((535,672),(500,530))}
# 손 그림표(hands_sheet.jpg: 손 두 개만, 손목이 위): 각 손을 크기 맞춰 720x1280 캔버스의 손목 자리에 아래로 늘어뜨려 놓는다
SHEET_WRIST={'hand_l':(297,213),'hand_r':(737,213)}; SHEET_SCALE=(0.23,0.19)   # 가로=손목 너비 맞춤, 세로=캐논 손 길이
if args.hands:
    if 'sheet' in os.path.basename(args.hands):
        sim=Image.open(P_(args.hands)).convert('RGB'); sim=Image.fromarray(cv2.erode(np.array(sim),np.ones((7,7),np.uint8))); tp=f'{TMP}/hsheet.png'; sim.save(tp); SA=rmbg(tp); SA[...,:3]=np.array(sim)
        HRA=np.zeros((H,W,4),np.uint8)
        for hn,(sx0,sy0) in SHEET_WRIST.items():
            half=SA[:, :512] if sx0<512 else SA[:, 512:]; ox=0 if sx0<512 else 512
            ys_,xs_=np.where(half[...,3]>128); y0=sy0+10   # 손목 윗변(밝은 끝)은 버림
            c=half[y0:ys_.max()+2, xs_.min():xs_.max()+1].copy(); cx=sx0-ox-xs_.min()
            ci=Image.fromarray(c); nw,nh=max(1,round(ci.width*SHEET_SCALE[0])),max(1,round(ci.height*SHEET_SCALE[1]))
            ci=np.array(ci.resize((nw,nh),Image.LANCZOS)); (wx,wy),_=HAND_SRC[hn]
            px=int(round(wx-cx*SHEET_SCALE[0])); py=int(wy-2)
            HRA[py:py+nh,px:px+nw]=ci
        sk_=HRA[...,:3][(HRA[...,3]>200)&(HRA[...,:3].astype(int).sum(-1)>650)].astype(float); fz_=(segdist(P,J['forearm_l'],J['hand_l'])<10)|(segdist(P,J['forearm_r'],J['hand_r'])<10); bk_=base[fz_&(BA[...,3]>200)&(base.sum(-1)>600)]
        if len(sk_) and len(bk_):
            gain=np.median(bk_,0)/np.median(sk_,0); HRA[...,:3]=np.clip(HRA[...,:3]*gain,0,255).astype(np.uint8); print('hand skin gain',gain.round(3))
        HAND_SRC={k:((v[0][0],v[0][1]),(v[0][0],v[0][1]-140)) for k,v in HAND_SRC.items()}
    else:
        im=Image.open(P_(args.hands)).convert('RGB').resize((W,H),Image.LANCZOS); tp=f'{TMP}/hands.png'; im.save(tp)
        HRA=rmbg(tp); HRA[...,:3]=np.array(im)
    for hn,fn in (('hand_l','forearm_l'),('hand_r','forearm_r')):
        (wx,wy),(ex,ey)=HAND_SRC[hn]; a_src=np.degrees(np.arctan2(wy-ey,wx-ex))
        w=np.array(J[hn],float); e=np.array(J[fn],float); a_dst=np.degrees(np.arctan2(*(w-e)[::-1]))
        ds=np.array([wx-ex,wy-ey],float); ds/=np.linalg.norm(ds); ts=(P-[wx,wy])@ds; qs=np.abs((P-[wx,wy])@np.array([-ds[1],ds[0]]))
        hsrc=HRA.copy(); hm_=(ts>-12)&(ts<130)&(qs<46)&(hsrc[...,3]>0); hm_=keep_big(hm_,500); hsrc[...,3]=hsrc[...,3]*hm_
        M=cv2.getRotationMatrix2D((wx,wy),a_src-a_dst,1.0); M[:,2]+=w-np.array([wx,wy])
        ha2=cv2.warpAffine(hsrc,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=0)
        d=(w-e)/np.linalg.norm(w-e); nr=np.array([-d[1],d[0]])
        def mid(A_,tt):   # 팔 방향 tt 위치에서 너비 가운데(q)
            qs_=[q for q in range(-60,60) if A_[int(round(w[1]+d[1]*tt+nr[1]*q)),int(round(w[0]+d[0]*tt+nr[0]*q))]]; return (min(qs_)+max(qs_))/2 if qs_ else 0
        sh=mid(BA[...,3]>128,-8)-mid(ha2[...,3]>128,8)   # 새 손을 팔뚝 가운데에 맞춰 옆으로 민다
        M[:,2]+=nr*sh; ha2=cv2.warpAffine(hsrc,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=0); print(hn,'side shift',sh)
        t=((P-w)@d); r=np.hypot(*(P-w).transpose(2,0,1))
        q=np.abs((P-w)@np.array([-d[1],d[0]])); zone=(t>-2)&(t<140)&(q<75); src=zone&(ha2[...,3]>0)
        # 새 손 아래 손목 바깥쪽은 비우고, 새 손을 넣는다. 손목 위 2~10px 는 섞어서 이음새를 감춘다
        BA=np.where((zone&~src)[...,None],0,BA)
        bl=np.clip((t+2)/8,0,1)[...,None]*src[...,None]
        BA=(BA*(1-bl)+ha2*bl).astype(np.uint8); base=np.where(src[...,None]&(bl>0.5),ha2[...,:3].astype(np.float32),base)
    alpha=BA[...,3]>128
# 팔·손 바깥선 다시 그리기(정리): 실루엣을 4배로 키워 부드럽게 한 뒤 거리값으로 선 한 줄(AA)을 그림 → 계단·1px 꺾임 없음
def smooth_outline(base, BA, zone, width=2.6, sig=4.5, recolor=True):
    A=(BA[...,3]>128).astype(np.float32); S=4
    big=cv2.resize(A,(W*S,H*S),interpolation=cv2.INTER_LINEAR); big=cv2.GaussianBlur(big,(0,0),sig*S)>0.5
    din=ndimage.distance_transform_edt(big)/S; dout=ndimage.distance_transform_edt(~big)/S
    sd=cv2.resize((din-dout).astype(np.float32),(W,H),interpolation=cv2.INTER_AREA)   # 안쪽 +, 바깥 -
    a_new=np.clip((sd+1.0)/2.0,0,1)
    # 선 안쪽 색: 가장자리에서 4px 안쪽 색을 끌어옴
    inner=(sd>width+4.5)&(A>0)
    _,(iy,ix)=ndimage.distance_transform_edt(~inner,return_indices=True); fill=base[iy,ix]
    t=np.clip((sd-width)/1.6+0.5,0,1)[...,None]   # 0=선, 1=안쪽
    col=OUTL*(1-t)+fill*t
    z=zone&(sd>-2)&(sd<width+4.5)&recolor
    if not recolor:   # 색은 그대로, 바깥 가장자리만: 밖으로 번진 곳은 선 색으로
        zz=zone&(sd>-2)&(sd<1.2)&(BA[...,3]<128); base[zz]=OUTL
    base[z]=col[z]; BA[...,:3][z]=base[z].astype(np.uint8); BA[...,3][zone]=(a_new[zone]*255).astype(np.uint8)
    return base,BA
# 손가락 사이 진한 분홍 그림자를 옅게(피부색 쪽으로 60%)
# 바깥선 정리: 몸 실루엣 바깥 2px 안의 밝은 점(회색 점·흰 홈·끊긴 선)을 선 색으로 채움 → 한 두께·한 색의 선
OUTL=np.median(base[alpha&(base.sum(-1)<260)],0)
ring=alpha&~ndimage.binary_erosion(alpha,iterations=2)
lt=ring&(base.sum(-1)>OUTL.sum()+90)
base[lt]=OUTL; BA[...,:3][lt]=OUTL.astype(np.uint8); print('outline fix px',int(lt.sum()),OUTL)
limbz=np.zeros((H,W),bool)
for hn,fn,un in (('hand_l','forearm_l','upperarm_l'),('hand_r','forearm_r','upperarm_r')):
    limbz|=(segdist(P,J[un],J[fn])<60)|(segdist(P,J[fn],J[hn])<60)|(segdist(P,J[hn],(103,716) if hn=='hand_l' else (634,716))<75)
limbz&=(yy>480)
handz=limbz&((segdist(P,J['hand_l'],(103,716))<70)|(segdist(P,J['hand_r'],(634,716))<70))
bv=base; pk=handz&(bv[...,0]-bv[...,1]>38)&(bv.sum(-1)>430)&(BA[...,3]>128)
skinc=np.median(base[handz&(BA[...,3]>200)&(bv.sum(-1)>700)],0)
nearl=ndimage.binary_dilation(handz&(bv.sum(-1)<430),iterations=3)
pk2=pk&nearl; pk1=pk&~nearl
base[pk2]=skinc; base[pk1]=base[pk1]*0.55+skinc*0.45; pk=pk1|pk2
base[pk]=base[pk]; BA[...,:3][pk]=base[pk].astype(np.uint8); print('finger pink px',int(pk.sum()))
# 손가락 안쪽 선: 붙어 있는 진한 선 2~3줄을 가운데 한 줄(AA)로 합침
from skimage.morphology import skeletonize
inn=handz&ndimage.binary_erosion(BA[...,3]>128,iterations=5)
dkh=inn&(base.sum(-1)<540)
dkc=ndimage.binary_closing(dkh,iterations=2)&inn
skl=keep_big(skeletonize(dkc),10)
if 'sheet' in os.path.basename(args.hands or ''): dkc[:]=False
lineA=np.clip(1.7-ndimage.distance_transform_edt(~skl),0,1)[...,None]
R=ndimage.binary_dilation(dkc,iterations=1)&inn
base[R]=(skinc*(1-lineA)+OUTL*lineA)[R]; BA[...,:3][R]=base[R].astype(np.uint8); print('finger lines px',int(R.sum()))
base,BA=smooth_outline(base,BA,limbz&~handz if 'sheet' in os.path.basename(args.hands or '') else limbz)
if 'sheet' in os.path.basename(args.hands or ''): base,BA=smooth_outline(base,BA,handz,width=2.4,sig=1.2,recolor=False)   # 손: 손가락 틈은 살리고 계단만 매끈하게
alpha=BA[...,3]>128
_h=ndimage.binary_fill_holes(alpha)&~alpha; _h=_h&~keep_big(_h,200)   # 다시 그리며 생긴 작은 틈(겨드랑이)만 메움
if _h.any():
    _,(iy,ix)=ndimage.distance_transform_edt(~alpha,return_indices=True); base[_h]=base[iy[_h],ix[_h]]; BA[_h]=BA[iy[_h],ix[_h]]; BA[...,3][_h]=255; alpha=BA[...,3]>128
Image.fromarray(BA).save(f'{OUT}/base_aligned.png')   # 검사용(실루엣 기준)
limb=[b for b in BONES if b[0] not in ('root','arm_up_r')]; names=[b[0] for b in limb]
D=np.stack([segdist(P,b[2],b[3]) for b in limb]); own=np.argmin(D,0)
TORSO=('head','neck','chest','pelvis')
def band(n):
    y0={'head':0,'neck':300,'chest':352,'pelvis':590}[n]; y1={'head':300,'neck':352,'chest':590,'pelvis':712}[n]; return (yy>=y0)&(yy<y1)
core=np.isin(own,[names.index(n) for n in TORSO])
# 맨몸 그림의 흰 민소매·반바지(옷 밑에 숨어야 할 곳)
white=(base.min(-1)>240)&(np.ptp(base,axis=-1)<8)&alpha
tank=white&(yy>300)&(yy<600)&(xx>255)&(xx<465); shorts=white&(yy>=540)&(yy<780)&(xx>230)&(xx<490)
edt=ndimage.distance_transform_edt(alpha)
atts=[]
for i,n in enumerate(names):
    reg=(own==i)&alpha
    if n in TORSO: reg=core&band(n)&alpha
    if n=='chest': reg|=ndimage.binary_dilation(tank,iterations=2)&alpha&np.isin(own,[names.index(x) for x in names if x.startswith(('upperarm','forearm','hand'))])  # 팔에서 뺀 민소매는 가슴이 갖는다
    if n.startswith(('upperarm','forearm','hand')): reg=reg&~ndimage.binary_dilation(tank,iterations=2)   # 팔 조각엔 민소매 없음
    m=(ndimage.distance_transform_edt(~reg)<=OVERLAP)&alpha
    # 둥근 관절 덮개: 자기 시작 관절에 (팔·다리 반폭+2px) 원 → 돌아가도 꺾인 모서리가 안 보임
    if not n in TORSO:
        jx,jy=J[n]; r=edt[jy,jx]+2 if alpha[jy,jx] else 20
        disk=((xx-jx)**2+(yy-jy)**2<=r*r)&alpha
        m|=disk
    if n.startswith(('upperarm','forearm','hand')): m=keep_big(m&ndimage.binary_dilation(ndimage.binary_opening(m,iterations=2),iterations=3),2000)   # 부스러기만 빼고 끝 모서리 선은 살림
    if n=='pelvis': m|=(np.isin(own,[names.index('thigh_l'),names.index('thigh_r')])&(yy<712+OVERLAP)&(yy>=590)&alpha)
    sc=(HAND_SCALE,J[n]) if n.startswith('hand') else None
    mf=m.astype(float)
    if n not in ('head','pelvis','chest'):
        # 안쪽 자른 선(다른 조각과 닿는 곳)은 4px 부드럽게 → 이음새·가로줄·호(弧) 선이 안 보임. 밑 조각이 같은 그림이라 티가 안 난다
        jx_,jy_=J[n]; cut=alpha&~m&(((xx-jx_)**2+(yy-jy_)**2)<75**2)   # 자기 시작 관절 쪽(위에 그려지는 쪽)만 부드럽게; 끝 쪽은 위 조각이 덮음
        dint=ndimage.distance_transform_edt(~cut)
        mf=mf*np.clip((dint-0.5)/4,0,1)
    atts.append(save_part(n,BA,mf,n,scale=sc))
# 눈 감기
ec,EA=load(args.eyes)
diff=np.abs(ec-base).max(-1); ez=(yy>140)&(yy<240)&(xx>240)&(xx<480)
em=ndimage.binary_closing(ndimage.binary_dilation((diff>30)&ez,iterations=6),iterations=4)
em=ndimage.gaussian_filter(em.astype(float),1.2)*alpha
eyes=save_part('eyes_closed',np.dstack([ec,np.full((H,W),255,np.float32)]).astype(np.uint8),em,'head')
# 머리카락: 분홍 + 붙은 바깥선만, 작은 부스러기·흰 점 제거
hr,HA=load(args.hair); ha=HA[...,3]>128
bgc=np.median(np.r_[hr[:8].reshape(-1,3),hr[:,:8].reshape(-1,3)],0)
gap=keep_big((np.abs(hr-bgc).max(-1)<=16)&ha,30); ha&=~gap   # 머리카락 사이에 갇힌 배경색만 뺀다(바깥 가장자리는 부드럽게 둔다)
pink=(hr[...,0]-hr[...,1]>30)&(hr[...,0]>170)&(hr[...,2]-hr[...,1]>-2)&ha&(yy<720)   # 분홍 머리(피부 그림자는 B<G 라 빠짐)
dark=(hr.sum(-1)<420)&ha
hm=pink|(ha&ndimage.binary_dilation(pink,iterations=4)&~ndimage.binary_dilation(alpha&~pink,iterations=0)&~(alpha&(np.abs(hr-base).max(-1)<30)))
hm|=(HA[...,3]>40)&(hr.sum(-1)<500)&~gap&ndimage.binary_dilation(pink,iterations=5)   # 바깥 진한 선과 그 경계 픽셀까지 포함(끊긴 점선 방지)
hm|=(HA[...,3]>40)&ndimage.binary_dilation(pink,iterations=3)&ndimage.binary_dilation((hr.sum(-1)<430),iterations=3)&~gap   # 선과 분홍 사이 밝은 AA 픽셀(빠지면 구멍처럼 보임)
hm=ndimage.binary_closing(hm,iterations=2); hm=ndimage.binary_fill_holes(hm)&(HA[...,3]>40)&~gap
hm=hm&~((hr.min(-1)>225)&(np.ptp(hr,axis=-1)<22)&~ndimage.binary_dilation(pink,iterations=2))      # 흰 점(분홍에 붙은 하이라이트는 남기고 아래에서 선과 떼어 놓음)
hm=keep_big(hm,900)   # (opening 은 가는 바깥선을 지워서 안 씀)
# 안쪽 자른 선(머리카락이 피부·옷과 닿던 곳)의 밝은 테두리 2px 는 버린다 → 흰 줄 없음
ring=hm&~ndimage.binary_erosion(hm,iterations=2)
hm&=~(ring&~pink&~dark&alpha)
front=hm&alpha&(yy<300); back=hm&~front
armz=ndimage.binary_dilation(np.isin(own,[names.index(x) for x in names if x.startswith(('upperarm','forearm','hand'))])&alpha,iterations=3)
armz|=(segdist(P,J['hand_l'],(103,716))<70)|(segdist(P,J['hand_r'],(634,716))<70)   # 손 근처(다른 그림의 손 선)는 머리카락 아님
back=keep_big(back&~armz&~(ndimage.binary_dilation(armz,iterations=12)&(yy>470)&(yy<580)),600)   # 팔꿈치 둘레 머리 끝 조각·배경 틈 정리    # 팔 위에 걸친 머리카락은 뒤로 못 감 → 뺀다(팔이 움직이면 떨어져 보임)
# 뒷머리는 몸 뒤로 8px 더 들어가게(가장자리 색 번짐): 옷이 몸보다 넓어도 머리카락과 옷 사이에 배경이 안 비친다
ext=ndimage.binary_dilation(back,iterations=8)&~back&ndimage.binary_dilation(alpha,iterations=6)&(yy<720)&~(ndimage.binary_dilation(armz,iterations=6)&(yy>525))
# 머리 윗부분 하이라이트가 바깥선에 붙어 흰 테처럼 보이지 않게: 선에서 2px 안의 밝은 점은 분홍으로 메움(하이라이트는 2px 안쪽으로 물러남)
hv=HA[...,:3].astype(int); hdk=hm&(hv.sum(-1)<430)
hl=hm&(hv.sum(-1)>672)&ndimage.binary_dilation(hdk,iterations=3)&(yy<400)
HA=HA.copy(); HA[...,:3]=cv2.inpaint(np.ascontiguousarray(HA[...,:3]),(ndimage.binary_dilation(hl,iterations=1)&hm&~hdk).astype(np.uint8)*255,3,cv2.INPAINT_TELEA); print('hair hl px',int(hl.sum()))
_,(iy,ix)=ndimage.distance_transform_edt(~back,return_indices=True)
HB=HA.copy(); HB[ext,:3]=HA[iy[ext],ix[ext],:3]; HB[ext,3]=255
hb=save_part('hair_back',HB,back|ext,'head'); hf=save_part('hair_front',HA,front,'head')
def cut_wave_arm(prefix, fname, normal_rgb):
    """흔드는 팔(오른쪽)만: 윗팔+소매 한 장(가슴뼈), 아래팔+손 한 장(팔꿈치 축, 둥근 덮개)."""
    wr,WA=load(fname); wa=WA[...,3]>128
    rg=wa&~ndimage.binary_erosion(wa,iterations=2); lt=rg&(wr.sum(-1)>OUTL.sum()+90); WA[...,:3][lt]=OUTL.astype(np.uint8); wr[lt]=OUTL   # 바깥선 흰 점 메우기
    diff=np.abs(wr-normal_rgb).max(-1)>30
    zone=(xx>446)&(yy<570)&(yy>200)
    arm=keep_big(ndimage.binary_closing(wa&zone&ndimage.binary_dilation(diff,iterations=6),iterations=2),3000)
    # 소매: 보통 자세에서 윗팔뼈 쪽 노란 옷(어깨 솔기 근처까지)
    yel=(wr[...,0]>200)&(wr[...,1]>180)&(wr[...,2]<175)&wa
    sleeve=yel&(own==names.index('upperarm_r'))&(yy<490)
    arm=keep_big(arm|sleeve|(wa&(wr.sum(-1)<430)&ndimage.binary_dilation(sleeve,iterations=3)&(own==names.index('upperarm_r'))),3000)
    arm=ndimage.binary_fill_holes(arm)
    # 몸통과 닿는 자르는 선은 6px 부드럽게(두 그림의 아주 작은 차이가 선으로 안 보이게)
    inner=wa&~arm; d=ndimage.distance_transform_edt(~inner)
    soft=np.clip((d-1)/6,0,1)*arm
    # 팔 전체(소매+윗팔+아래팔+손)를 한 장으로: 그림 그대로라 이음새가 없다. 어깨 안쪽 축으로 살짝 흔든다.
    soft=despeck(WA,soft); WA2,_=clean_hem(WA,soft)
    return save_part(f'{prefix}arm_up_r',WA2,soft,'arm_up_r',ds=True)
wave_body=cut_wave_arm('',args.base_wave,base)
# 옷
cloth=[]
def cut_outfit(oname, fname):
    fname,_,wfile=fname.partition(',')
    ot,OA=load(fname); oa=OA[...,3]>128
    R,G,Bc=ot[...,0],ot[...,1],ot[...,2]
    od=np.abs(ot-base).max(-1)
    dark=(ot.sum(-1)<430)&oa
    def with_line(m,px=4): return (m|(dark&ndimage.binary_dilation(m,iterations=px)))&oa
    yellow=(R>200)&(G>180)&(Bc<175)&(R-Bc>50)&oa&(yy<640)
    blue=(Bc-R>20)&(Bc>150)&oa&(yy>520)&(yy<860)
    red=(R-G>70)&(R>140)&oa&(yy>1080)
    sockw=(ot.min(-1)>215)&(np.ptp(ot,axis=-1)<28)&oa&(yy>1020)&(od>12)
    yellow_out=np.zeros_like(yellow)
    wcov=ndimage.binary_dilation(white&(yy>288)&(yy<600)&(xx>240)&(xx<525),iterations=3)&oa   # 맨몸의 흰 곳이 옷 가장자리로 비치지 않게
    top=ndimage.binary_fill_holes(with_line(keep_big(ndimage.binary_closing(yellow,iterations=3),3000)))
    top|=ndimage.binary_dilation(tank,iterations=3)&oa&ndimage.binary_dilation(top,iterations=6)&~yellow_out  # 민소매 자리는 옷 그림으로 덮기
    top|=wcov&ndimage.binary_dilation(top,iterations=8)
    skirt=ndimage.binary_fill_holes(with_line(keep_big(ndimage.binary_closing(blue,iterations=3),3000)))
    skirt|=ndimage.binary_dilation(shorts,iterations=3)&oa&(yy<820)
    skirt=skirt&~np.isin(own,[names.index(x) for x in names if x.startswith(('forearm','hand'))])
    skirt=keep_big(skirt,3000)
    for side in 'lr':
        legs=np.isin(own,[names.index(f'shin_{side}'),names.index(f'foot_{side}')])
        so=keep_big(ndimage.binary_closing(sockw&legs,iterations=2),300)
        so=ndimage.binary_fill_holes(with_line(so,3))&legs
        sh=ndimage.binary_fill_holes(with_line(keep_big(red&legs,300),3))&legs
        sh=ndimage.binary_opening(ndimage.binary_closing(sh,iterations=3),iterations=2)   # 밑창 가장자리 톱니 없애기
        sh=ndimage.gaussian_filter(sh.astype(float),0.9)   # 한 줄 AA 가장자리
        for k,mm,bone in (('socks',so,f'shin_{side}'),('shoes',sh,f'foot_{side}')):
            a=save_part(f'{oname}_{k}_{bone}',OA,mm,bone); a.update(kind=k,outfit=oname,slot=f'{k}_{side}'); cloth.append(a)
        # 신발 신은 발: 맨발 발가락이 신발 밑창 아래로 삐져나오지 않게, 신발 안쪽(1px 넓힘)만 남긴 발 조각
        fi=names.index(f'foot_{side}'); fm=(ndimage.distance_transform_edt(~(own==fi))<=OVERLAP)&alpha&(ndimage.binary_erosion(sh>0.5,iterations=3)|so)
        a=save_part(f'{oname}_inshoe_foot_{side}',BA,fm,f'foot_{side}'); a.update(kind='inshoe',outfit=oname,slot=f'foot_{side}'); cloth.append(a)
        # 양말 신은 정강이: 양말 높이에서 양말 밖으로 나온 맨다리 선(양말 옆 진한 줄)을 뺀다
        si=names.index(f'shin_{side}'); sm=(ndimage.distance_transform_edt(~(own==si))<=OVERLAP)&alpha
        jx,jy=J[f'shin_{side}']; r=edt[jy,jx]+2; sm|=((xx-jx)**2+(yy-jy)**2<=r*r)&alpha
        rows=np.where(so.any(1))[0]; sb=(yy>=rows.min()+3)&(yy<=rows.max()) if len(rows) else np.zeros_like(so)
        sm&=~(sb&~ndimage.binary_erosion(so,iterations=2))
        dint=ndimage.distance_transform_edt(~(alpha&~sm&(((xx-jx)**2+(yy-jy)**2)<75**2))); smf=sm*np.clip((dint-0.5)/4,0,1)
        a=save_part(f'{oname}_insock_shin_{side}',BA,smf,f'shin_{side}'); a.update(kind='insock',outfit=oname,slot=f'shin_{side}'); cloth.append(a)
    # 소매: 윗팔뼈 쪽 노란 옷 + 어깨 회전축 둘레 원(돌려도 어깨 위를 늘 덮음). 몸통 윗옷은 그대로 둔다(어깨 덮개).
    for side in 'lr':
        ix=names.index(f'upperarm_{side}'); jx,jy=J[f'upperarm_{side}']
        sl=top&(own==ix)
        sl|=top&(((xx-jx)**2+(yy-jy)**2)<=46**2)
        sl=keep_big(sl,500)
        sl=despeck(OA,sl); OA2,nl=clean_hem(OA,sl); print('hem',side,nl)
        a=save_part(f'{oname}_sleeve_upperarm_{side}',OA2,sl,f'upperarm_{side}',ds=True); a.update(kind='sleeve',outfit=oname,slot=f'sleeve_{side}'); cloth.append(a)
    for k,mm,bone,slot in (('top',top,'chest','top'),('bottom',skirt,'pelvis','bottom')):
        mm=despeck(OA,mm); OA2=clean_hem(OA,mm)[0] if k=='top' else OA
        a=save_part(f'{oname}_{k}_{bone}',OA2,mm,bone,ds=True); a.update(kind=k,outfit=oname,slot=slot); cloth.append(a)
    if wfile:
        a1=cut_wave_arm(f'{oname}_',wfile,ot); a1.update(kind='wave',outfit=oname,slot='arm_up_r'); cloth.append(a1)
for on,fn in OUTFITS.items(): cut_outfit(on,fn)
# 장식(리본, 별 핀)
AC=rmbg(P_(args.accs)); lab,n=ndimage.label(AC[...,3]>128); sz=ndimage.sum(AC[...,3]>128,lab,range(1,n+1))
big=sorted([i+1 for i,s in enumerate(sz) if s>2000],key=lambda i:np.where(lab==i)[1].mean())
accs=[save_part(nm,AC,ndimage.binary_dilation(lab==i,iterations=3),None) for nm,i in zip(['acc_ribbon','acc_star'],big)]
hair_top=int(np.where(hm[:, 400:470].any(1))[0].min())
json.dump({'size':[W,H],'bones':BONES,'atts':atts,'eyes':eyes,'hair':[hb,hf],'cloth':cloth,'accs':accs,'hair_top_y':hair_top,'hand_scale':HAND_SCALE,'wave_body':wave_body},open(f'{OUT}/build.json','w'),indent=1)
shutil.rmtree(TMP,ignore_errors=True)
print('ok',len(atts),'cloth',len(cloth),'hair_top',hair_top)
