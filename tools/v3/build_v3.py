"""시하 v4 조각 파이프라인: 생성 그림(GenerateImage) → 정렬 → 선 다듬기(2배 고해상도) → 조각 자르기.
코드는 배경 지우기·정렬·자르기·투명·선 매끈하게만 한다(새로 그리지 않음)."""
import os, sys, json, numpy as np, cv2
from PIL import Image
from scipy import ndimage
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
from rmbg import rmbg
RAW=sys.argv[1] if len(sys.argv)>1 else f'{HERE}/raw'; OUT=sys.argv[2] if len(sys.argv)>2 else f'{HERE}/out'
W,H,S=720,1280,2                          # 원본 720x1280 → 결과 1440x2560
os.makedirs(f'{OUT}/parts',exist_ok=True); TMP=f'{OUT}/_tmp'; os.makedirs(TMP,exist_ok=True)
gray=lambda x: cv2.cvtColor(x.astype(np.uint8),cv2.COLOR_RGB2GRAY).astype(np.float32)
REF=np.array(Image.open(f'{RAW}/body.jpg').convert('RGB').resize((W,H))).astype(np.float32)
def load(name, align=True):
    im=Image.open(f'{RAW}/{name}').convert('RGB').resize((W,H),Image.LANCZOS); tp=f'{TMP}/{name}.png'; im.save(tp)
    rgb=np.array(im).astype(np.float32); a=rmbg(tp).astype(np.float32)
    bgc=np.median(np.r_[rgb[:8].reshape(-1,3),rgb[:,:8].reshape(-1,3),rgb[:,-8:].reshape(-1,3)],0)
    nb=np.abs(rgb-bgc).max(-1)<10; nb=ndimage.binary_opening(nb,iterations=2); a[...,3][nb]=0   # 갇힌 배경(팔과 머리 사이) 투명
    if align:
        M=np.eye(2,3,dtype=np.float32)
        try: _,M=cv2.findTransformECC(gray(REF),gray(rgb),M,cv2.MOTION_AFFINE,(3,300,1e-6),None,5)
        except cv2.error: pass
        f=cv2.INTER_CUBIC+cv2.WARP_INVERSE_MAP
        rgb=cv2.warpAffine(rgb,M,(W,H),flags=f,borderMode=cv2.BORDER_REPLICATE); a=cv2.warpAffine(a,M,(W,H),flags=f)
    return np.clip(rgb,0,255), np.clip(a[...,3],0,255)/255
def smooth01(x,a,b): t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
LINE_R=2.4
LINE=np.array([0x6E,0x3D,0x5B],np.float32)
def hires(rgb, al, keep_boxes=(), redraw=True):
    """선을 따로 떼어 2배로 키운 뒤 매끈하게 다시 문턱(AA 한 줄), 바탕색은 선을 지우고 키움. 눈·입 상자는 원래 그림을 키워서 쓴다."""
    h0,w0=rgb.shape[:2]
    lum=gray(rgb); k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7))
    fill=cv2.morphologyEx(rgb,cv2.MORPH_CLOSE,k)            # 가는 진한 선 지운 바탕
    lf=gray(fill); line=np.clip((lf-lum)/np.maximum(lf-95,30),0,1)  # 선 진하기 0..1
    line[al<0.02]=0
    up=lambda x,i=cv2.INTER_CUBIC: cv2.resize(x,(w0*S,h0*S),interpolation=i)
    # 바깥 테두리도 선으로: 알파 가장자리에서 선을 이어 그린다
    A=smooth01(cv2.GaussianBlur(up(al),(0,0),1.1),0.35,0.65)
    L0=cv2.GaussianBlur(up(line),(0,0),1.0)
    from skimage.morphology import skeletonize, remove_small_objects
    bm=ndimage.binary_closing(L0>0.18,structure=np.ones((3,3)),iterations=2)
    sk=skeletonize(remove_small_objects(bm,max_size=60))       # 선 가운데 한 줄 → 일정한 굵기로 다시 그음
    lb_,n_=ndimage.label(sk,structure=np.ones((3,3)))
    if n_: sz_=ndimage.sum(sk,lb_,range(1,n_+1)); sk=np.isin(lb_,[i+1 for i,v in enumerate(sz_) if v>=40])   # 짧은 토막 선(점선·잔점) 버림
    d=ndimage.distance_transform_edt(~sk); L=np.clip(LINE_R+0.5-d,0,1)
    L*=np.clip(ndimage.maximum_filter(L0,9)/0.5,0.3,1)   # 원래 옅은 선(옷 주름)은 같은 굵기·옅은 색으로
    L=np.maximum(L,smooth01(L0,0.3,0.6)*ndimage.binary_dilation(sk,iterations=4))     # 뼈선이 끊긴 곳은 원래 선(매끈하게)으로 이어 줌 → 끊김 없음
    # 잔점 지우기: 아주 작은 선 덩어리 제거
    lb,n=ndimage.label(L>0.5)
    if n: sz=ndimage.sum(np.ones_like(L),lb,range(1,n+1)); small=np.isin(lb,[i+1 for i,s in enumerate(sz) if s<80]); L[ndimage.binary_dilation(small,iterations=2)]=0
    # 바깥 선 밖의 밝은 테두리(후광) 자르기: 바깥 선 안쪽만 남김
    R=ndimage.binary_fill_holes((L>0.3)|ndimage.binary_erosion(A>0.5,iterations=8))
    A=np.minimum(A,cv2.GaussianBlur(R.astype(np.float32),(0,0),0.6))
    # 바깥 테두리 선: (후광 자른 뒤) 실루엣 가장자리를 따라 같은 굵기로 한 줄(끊김 없음, 이중선 없음)
    ed=ndimage.distance_transform_edt(ndimage.binary_fill_holes(A>0.5)); Ledge=np.clip(LINE_R*2+0.5-ed,0,1)*np.clip(ed+0.5,0,1)
    L=np.maximum(L,Ledge)
    F=cv2.resize(fill,(w0*S,h0*S),interpolation=cv2.INTER_LANCZOS4); F=cv2.GaussianBlur(F,(0,0),0.7)
    out=F*(1-L[...,None])+LINE*L[...,None]
    O=np.clip(up(rgb,cv2.INTER_LANCZOS4),0,255)
    if not redraw:   # 머리카락처럼 가는 결이 많은 그림: 선을 다시 긋지 않고 잡티만 눌러 매끈하게 키움
        O2=cv2.bilateralFilter(rgb.astype(np.float32),5,18,3); O2=cv2.resize(O2,(w0*S,h0*S),interpolation=cv2.INTER_LANCZOS4)
        out=cv2.bilateralFilter(np.clip(O2,0,255).astype(np.float32),7,14,2.5); keep_boxes=()
        out=out*(1-Ledge[...,None])+LINE*Ledge[...,None]
    for (x0,y0,x1,y1) in keep_boxes:                         # 눈·입: 원래 그림 그대로 키움(가장자리 부드럽게 섞음)
        m=np.zeros((h0*S,w0*S),np.float32); m[y0*S:y1*S,x0*S:x1*S]=1; m=cv2.GaussianBlur(m,(0,0),6)
        out=out*(1-m[...,None])+O*m[...,None]
    # 안쪽 빈틈(머리카락 사이로 보이는 배경)의 밝은 테두리 자르기: 빈틈에서 밝은 화소만 따라 4px 넓혀 투명
    Ab=A>0.5; pocket=ndimage.binary_fill_holes(Ab)&~Ab
    if pocket.any():
        grow=ndimage.binary_dilation(pocket,iterations=5,mask=(gray(np.clip(out,0,255))>212)|pocket)
        A=np.minimum(A,1-cv2.GaussianBlur(grow.astype(np.float32),(0,0),0.6))
    return np.dstack([np.clip(out,0,255),A*255]).astype(np.uint8)
def save(name, rgba, mask=None):
    a=rgba.copy()
    if mask is not None: a[...,3]=(a[...,3]*mask).astype(np.uint8)
    ys,xs=np.where(a[...,3]>0)
    if not len(ys): raise SystemExit(f'빈 조각 {name}')
    x0,y0,x1,y1=xs.min(),ys.min(),xs.max()+1,ys.max()+1
    Image.fromarray(a[y0:y1,x0:x1]).save(f'{OUT}/parts/{name}.png',optimize=True)
    return {'path':f'parts/{name}.png','x':int(x0),'y':int(y0),'width':int(x1-x0),'height':int(y1-y0)}

# ---------- 좌표(원본 720x1280 기준) ----------
EYES=(270,180,455,262); MOUTH=(330,258,392,300); KEEP=[EYES,MOUTH]
CUT=640            # 허리 자르는 선(반바지·치마 안). 위=chest 뼈(숨쉬기), 아래=pelvis
OV=6               # 겹침(px, 원본 기준)
FIST=(220,276,286,342)        # 마이크 쥔 오른손(보는 쪽 왼쪽)
ELBOW=(545,466)
WAVE_BOX=(455,150,720,520); WAVE_PIVOT=(528,440); WAVE_Y0,WAVE_Y1=422,372; WAVE_X=501
WAVE_ANGLES=[-10,-7.5,-5,-2.5,0,2.5,5,7.5,10]
GRIP=(259,309); ELBOW_R=(206,494)   # 마이크 쥔 손 가운데, 그 팔 팔꿈치    # 흔드는 팔 팔꿈치(회전축), 이 선 위가 아래팔 조각
if __name__=='__main__':
    yy,xx=np.mgrid[0:H*S,0:W*S]/S
    def lay(name, keep=KEEP, align=True, redraw=True):
        rgb,al=load(name,align); return hires(rgb,al,keep,redraw), rgb, al
    body,brgb,bal=lay('body.jpg',align=False); outfit,orgb,oal=lay('outfit.jpg')
    bw,_,_=lay('body_wave.jpg'); ow,owrgb,_=lay('outfit_wave.jpg'); eyes,_,_=lay('eyes_closed.jpg'); hair,hrgb,hal=lay('hair.jpg',redraw=False)
    up=lambda m: cv2.resize(m.astype(np.float32),(W*S,H*S),interpolation=cv2.INTER_LINEAR)
    soft=lambda m,s=1.0: cv2.GaussianBlur(m.astype(np.float32),(0,0),s)
    P={}
    # 옷 = 맨몸과 다른 곳(목 아래)
    def cloth(rgb,al,ref=brgb):
        d=np.abs(rgb-ref).max(-1); m=((d>45)|(bal<0.5))&(al>0.5); m[:300]=False
        m=ndimage.binary_opening(m,iterations=2); m=ndimage.binary_closing(m,iterations=3); m=ndimage.binary_fill_holes(m)
        lb,n=ndimage.label(m); sz=ndimage.sum(m,lb,range(1,n+1)); m=np.isin(lb,[i+1 for i,s in enumerate(sz) if s>800])
        return ndimage.binary_dilation(m,iterations=2)
    cm=up(cloth(orgb,oal))>0.5; cmw=up(cloth(owrgb,_al:=load('outfit_wave.jpg')[1]))>0.5
    cm_soft=soft(cm,0.8)
    upper=(yy<CUT+OV).astype(np.float32); lower=(yy>=CUT).astype(np.float32)
    fa=((xx>495)&(yy<ELBOW[1]+OV)&(yy>180)).astype(np.float32)          # 흔드는 아래팔
    P['pelvis']=save('body_lower',body,lower); P['chest']=save('body_upper',body,upper)
    # 손 흔들기: 아래팔만 팔꿈치 위에서 부드럽게 휘어 돌린 그림을 각도별로 미리 만든다(자름선 없음 → 틈·꺾임 없음)
    RX0,RY0,RX1,RY1=WAVE_BOX; reg=np.zeros((H*S,W*S),bool); reg[RY0*S:RY1*S,RX0*S:RX1*S]=True
    # 흔들기 자세는 '바뀐 곳(팔·소매)'만 흔들기 그림에서 가져오고 나머지는 쉬는 자세 그림 그대로 → 흔들기 시작할 때 몸·옷이 바뀌지 않음
    bwrgb,bwal=load('body_wave.jpg'); owal=load('outfit_wave.jpg')[1]
    dm=((np.abs(bwrgb-brgb).max(-1)>30)|(np.abs(owrgb-orgb).max(-1)>30)|(np.abs(bwal-bal)>0.5)|(np.abs(owal-oal)>0.5)); dm[:, :430]=False; dm[:150]=False; dm[740:]=False
    dm=ndimage.binary_opening(dm,iterations=1); dm=ndimage.binary_closing(ndimage.binary_dilation(dm,iterations=6),iterations=6); dm=ndimage.binary_fill_holes(dm)
    lb,n=ndimage.label(dm); sz=ndimage.sum(dm,lb,range(1,n+1)); dm=np.isin(lb,[i+1 for i,s_ in enumerate(sz) if s_>2000])
    Mw=soft(up(dm)>0.5,2.0); Image.fromarray((dm*255).astype(np.uint8)).save(f'{TMP}/wave_mask.png')
    dmb=ndimage.binary_dilation(dm,iterations=20); json.dump({'wave_change_box':[int(v) for v in (np.where(dmb.any(0))[0].min(),np.where(dmb.any(1))[0].min(),np.where(dmb.any(0))[0].max()+1,np.where(dmb.any(1))[0].max()+1)]},open(f'{OUT}/wave_meta.json','w'))
    def blend(a,b,m):   # 미리 곱한 알파로 섞음
        A_=a.astype(np.float32); B_=b.astype(np.float32); m=m[...,None]
        pa=A_[...,:3]*A_[...,3:]/255; pb=B_[...,:3]*B_[...,3:]/255; al=A_[...,3:]*(1-m)+B_[...,3:]*m; pc=pa*(1-m)+pb*m
        return np.dstack([np.where(al>0,pc/np.maximum(al,1e-3)*255,0),al]).clip(0,255).astype(np.uint8)
    bw=blend(body,bw,Mw); ow=blend(outfit,ow,Mw)
    cmw_soft=cm_soft*(1-Mw)+soft(cmw,0.8)*Mw
    P['chest_wave']=save('body_upper_wave',bw,upper*~reg)
    P['basic_chest_wave']=save('basic_upper_wave',ow,upper*cmw_soft*~reg)
    wx=np.maximum(smooth01(xx,WAVE_X-5,WAVE_X+5),smooth01(-(yy-340),0,15))   # 손 쪽(위)은 엄지까지 모두, 소매 높이에서는 아래팔만
    wgt=smooth01(-(yy-WAVE_Y0),0,WAVE_Y0-WAVE_Y1)*wx
    bA=bw[...,3]>128; lb,n=ndimage.label(bA&(wgt>0.01)&reg); sz=ndimage.sum(bA,lb,range(1,n+1))
    stray=(wgt>0.01)&reg&~(lb==(int(np.argmax(sz))+1))          # 아래팔과 안 붙은 부스러기는 버림
    reg=reg&~stray
    cx,cy=WAVE_PIVOT; P['wave_frames']=[]
    for k,ang in enumerate(WAVE_ANGLES):
        th=np.deg2rad(ang)*wgt; c_,s_=np.cos(th),np.sin(th); dx,dy=xx-cx,yy-cy
        mx=((c_*dx+s_*dy)+cx)*S; my=((-s_*dx+c_*dy)+cy)*S     # 거꾸로 찾기(출력→원본)
        fr={}
        for nm,src,msk in (('body',bw,reg.astype(np.float32)),('basic',ow,reg*cmw_soft)):
            a_=src.astype(np.float32).copy(); a_[...,3]*=msk; a_[...,:3]*=a_[...,3:]/255   # 미리 곱한 알파로 휘기(가장자리 번짐 없음)
            wv=cv2.remap(a_,mx.astype(np.float32),my.astype(np.float32),cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
            al_=np.clip(wv[...,3],0,255); rgb_=np.where(al_[...,None]>0,wv[...,:3]/np.maximum(al_[...,None],1e-3)*255,0)
            fr[nm]=save(f'{nm}_wave_arm_{k}',np.dstack([np.clip(rgb_,0,255),al_]).astype(np.uint8))
        P['wave_frames'].append({'angle':ang,**fr})
    P['pelvis_wave']=save('body_lower_wave',bw,lower); P['basic_pelvis_wave']=save('basic_lower_wave',ow,lower*cmw_soft)
    P['basic_pelvis']=save('basic_lower',outfit,lower*cm_soft); P['basic_chest']=save('basic_upper',outfit,upper*cm_soft)
    fm=np.zeros((H*S,W*S),np.float32); x0,y0,x1,y1=FIST; fm[y0*S:y1*S,x0*S:x1*S]=1
    def segd(a,b):
        a=np.array(a,float);b=np.array(b,float);d=b-a;t=np.clip(((xx-a[0])*d[0]+(yy-a[1])*d[1])/(d@d),0,1); return np.hypot(xx-a[0]-t*d[0],yy-a[1]-t*d[1])
    arm=((segd(GRIP,ELBOW_R)<30)|(fm>0))&~cm    # 마이크 손잡이가 아래팔 뒤로 숨도록 주먹~팔꿈치까지 한 조각
    P['hand_r']=save('hand_r',body,soft(arm,1.0))
    em=np.zeros((H*S,W*S),np.float32); x0,y0,x1,y1=EYES; em[y0*S:y1*S,x0*S:x1*S]=1; em=soft(em,5)
    P['eyes_closed']=save('eyes_closed',eyes,em)
    # 머리카락: 분홍(R-G 큼, B>G) 영역
    r,g,b=[hrgb[...,i] for i in range(3)]
    pk=(((r-g>45)&(b>g+5))|(np.abs(hrgb-brgb).max(-1)>28))&(hal>0.5)
    pk=ndimage.binary_closing(pk,structure=np.ones((3,3)),iterations=5); pk=ndimage.binary_fill_holes(pk); pk=ndimage.binary_opening(pk&(hal>0.5),iterations=2)
    lb,n=ndimage.label(pk); sz=ndimage.sum(pk,lb,range(1,n+1)); pk=np.isin(lb,[i+1 for i,s in enumerate(sz) if s>1500])
    pk&=~ndimage.binary_dilation(cloth(orgb,oal)|False,iterations=0) if False else pk
    hm=soft(up(ndimage.binary_dilation(pk,iterations=1))>0.5,0.8)
    Image.fromarray((pk*255).astype(np.uint8)).save(f'{TMP}/hairmask.png')
    P['hair_back']=save('hair_back',hair,hm)
    hw,hwrgb,hwal=lay('hair_wave.jpg',redraw=False)
    r2,g2,b2=[hwrgb[...,i] for i in range(3)]; pk2=(((r2-g2>45)&(b2>g2+5))|(np.abs(hwrgb-bwrgb).max(-1)>28))&(hwal>0.5)
    pk2=ndimage.binary_closing(pk2,structure=np.ones((3,3)),iterations=5); pk2=ndimage.binary_fill_holes(pk2); pk2=ndimage.binary_opening(pk2&(hwal>0.5),iterations=2)
    same=(np.abs(hwrgb-bwrgb).max(-1)<26)&(bwal>0.3)&~((r2-g2>45)&(b2>g2+5))   # 흔들기 머리 그림 속 몸(팔) 화소 → 빼기(팔 둘레 흰 테 없음)
    pk2&=~ndimage.binary_dilation(same,iterations=2)
    pk2&=ndimage.binary_dilation((r2-g2>45)&(b2>g2+5),iterations=3)   # 분홍 머리 둘레 3px 안만(팔 테두리 선은 빠짐)
    hm2=soft(up(pk2)>0.5,0.8)
    dmh=ndimage.binary_dilation(dm,iterations=12); dmh[:330]=False   # 얼굴·귀 옆 머리는 쉬는 자세 그대로
    Mh=soft(up(dmh)>0.5,4.0)
    a1=hair.copy(); a1[...,3]=(a1[...,3]*hm).astype(np.uint8); a2=hw.copy(); a2[...,3]=(a2[...,3]*hm2).astype(np.uint8)
    a2[...,3]=(a2[...,3]*Mh).astype(np.uint8)
    def over(t,b):   # t 를 b 위에(미리 곱한 알파)
        T=t.astype(np.float32)/255; B=b.astype(np.float32)/255; ta=T[...,3:]; ba=B[...,3:]*(1-ta); al=ta+ba
        c=(T[...,:3]*ta+B[...,:3]*ba)/np.maximum(al,1e-4); return (np.dstack([c,al])*255).clip(0,255).astype(np.uint8)
    P['hair_back_wave']=save('hair_back_wave',over(a1,a2))   # 쉬는 자세 머리는 그대로 두고, 팔이 비켜 간 빈자리만 흔들기 머리 그림으로 채움
    bodyA=body[...,3]/255; front=hm*(soft(bodyA>0.5,1)) * (yy<300)*(1-soft(fm,1))
    P['hair_front']=save('hair_front',hair,front)
    json.dump(P,open(f'{OUT}/parts.json','w'),indent=1)
    print('ok',len(P))
