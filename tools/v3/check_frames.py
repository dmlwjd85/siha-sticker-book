"""프레임 전수 검사: check_frames.mjs 가 찍은 모든 프레임을 자동 비교한다.
검사(프레임마다):
 1) 떨어짐: 인형 실루엣 덩어리 수(쉬는 자세와 같아야 함) — 옷·머리·소품이 떨어져 나가면 늘어남
 2) 틈: 실루엣 안 새 가는 구멍(폭 6px 이하, 쉬는 자세에 없던 것) px
 3) 남음(잔상): 흔들기 프레임과 같은 시각 기준 프레임의 차이가 흔드는 팔 상자 밖에 생기면 안 됨
    + 흔드는 팔 상자 안에서 '팔 실루엣과 안 붙은' 옷·살색 조각이 있으면 남은 조각
 4) 이음새: 실루엣 안 한 줄 밝은 틈(양옆보다 밝은 1~2px 줄)이 쉬는 자세에 없던 자리에 생기면 안 됨
 5) 선 두께: 진한 선 픽셀의 두께 분포(중앙값·90%) — 쉬는 자세와 같아야 함(번짐·끊김 표시)
사용: python3 tools/v3/check_frames.py <프레임 폴더> [결과.json]"""
import json, sys, os, numpy as np
from PIL import Image
from scipy import ndimage
D=sys.argv[1]; OUTJ=sys.argv[2] if len(sys.argv)>2 else f'{D}/report.json'
L=json.load(open(f'{D}/frames.json'))
_BOX=None
def load(n):
    """프레임 읽기(인형 둘레만 잘라 빠르게). 자르는 상자는 첫 프레임 실루엣 + 여유 120px"""
    global _BOX, FULLW
    im=np.array(Image.open(f'{D}/{n}.png').convert('RGBA')).astype(np.int16); FULLW=im.shape[1]
    if _BOX is None:
        ys,xs=np.where(im[...,3]>0); _BOX=(max(ys.min()-120,0),ys.max()+120,max(xs.min()-120,0),xs.max()+120)
    y0,y1,x0,x1=_BOX; im=im[y0:y1,x0:x1]; return im
def comps(A):
    lb,n=ndimage.label(A); sz=ndimage.sum(A,lb,range(1,n+1)); return int((np.array(sz)>150).sum())
def hairish(im):
    r,g,b=im[...,0],im[...,1],im[...,2]; return (r-g>40)&(b>g)
IM_CUR=None
def holes(A, im=None):
    """가는 틈만(폭 6px 이하) 구멍으로 본다. 넓은 배경, 그리고 둘레 절반 넘게가 머리카락인 빈틈(머리카락 사이·머리와 손 사이로 보이는 배경)은 그림대로라 뺀다"""
    h=ndimage.binary_fill_holes(A)&~A; lb,n=ndimage.label(h)
    if not n: return h
    dt=ndimage.distance_transform_edt(h); mx=ndimage.maximum(dt,lb,range(1,n+1)); keep=[]
    hr=hairish(im) if im is not None else None
    for i,v in enumerate(mx):
        if v>3: continue
        if hr is not None:
            ring=ndimage.binary_dilation(lb==i+1,iterations=3)&~h
            if hr[ring].mean()>0.4: continue
        keep.append(i+1)
    return np.isin(lb,keep)
def seams(im,A):
    g=im[...,:3].mean(-1); inner=ndimage.binary_erosion(A,iterations=4)
    hx=(g-np.maximum(np.roll(g,2,1),np.roll(g,-2,1))>18); hy=(g-np.maximum(np.roll(g,2,0),np.roll(g,-2,0))>18)
    return (hx|hy)&inner&~ndimage.binary_dilation(hairish(im),iterations=1)   # 머리카락 결 사이 밝은 줄은 그림(이음새 아님)
def new_seams(s, base):
    """쉬는 자세에 없던 밝은 줄(12px 넘게 이어짐) 수"""
    s=s&~ndimage.binary_dilation(base,iterations=3); lb,n=ndimage.label(s); sz=ndimage.sum(s,lb,range(1,n+1)) if n else []
    return int(sum(1 for v in sz if v>=12))
def linew(im,A):
    dk=(im[...,:3].astype(int).sum(-1)<330)&A; d=ndimage.distance_transform_edt(dk)
    sk=dk&(d>=ndimage.maximum_filter(d,3)); v=d[sk]*2
    return (float(np.median(v)) if v.size else 0, float(np.percentile(v,90)) if v.size else 0)
res={'frames':len(L),'fail':[],'stats':{}}
for tag in ('basic','none'):
    fr=[f for f in L if (f['outfit'] or 'none')==tag]
    rest=load(f'{tag}_idle_000'); RA=rest[...,3]>128
    base_c=comps(RA); base_h=holes(RA,rest); base_S=seams(rest,RA); base_s=0; base_w=linew(rest,RA)
    sk=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'../../public/v3-demo/skeleton.json')))
    st={'rest_components':base_c,'rest_seams':base_s,'rest_linewidth':base_w,'max_new_hole':0,'max_out_of_box':0,'max_orphan':0,'max_seams':base_s,'linewidth_range':[base_w,base_w]}
    H,W=RA.shape; K=FULLW/(sk['skeleton']['width']+2*sk['skeleton']['stagePad']); PAD=sk['skeleton']['stagePad']
    x0,y0,x1,y1=sk['animations']['wave']['changeBox']   # 흔들기 때 바뀌어도 되는 상자(2배 좌표) → 화면 픽셀
    oy,ox=_BOX[0],_BOX[2]; box=np.zeros_like(RA); box[max(int(y0*K)-6-oy,0):int(y1*K)+6-oy,max(int((x0+PAD)*K)-6-ox,0):int((x1+PAD)*K)+6-ox]=True
    for f in fr:
        n=f['name']; im=load(n); A=im[...,3]>128
        c=comps(A); nh=int((holes(A,im)&~ndimage.binary_dilation(base_h,iterations=6)).sum()); s=new_seams(seams(im,A),base_S); w=linew(im,A)
        if c!=base_c: res['fail'].append([n,'떨어짐',c])
        if nh>20: res['fail'].append([n,'틈',nh])
        if s>0: res['fail'].append([n,'이음새',s])
        if abs(w[0]-base_w[0])>1.0: res['fail'].append([n,'선두께',w])
        st['max_new_hole']=max(st['max_new_hole'],nh); st['max_seams']=max(st['max_seams'],s)
        st['linewidth_range']=[min(st['linewidth_range'][0],w),max(st['linewidth_range'][1],w)]
        if '_wave_' in n:
            ref=load(n.replace('_wave_','_ref_')); d=np.abs(im-ref).max(-1)>40
            oob=int((d&~box).sum()); st['max_out_of_box']=max(st['max_out_of_box'],oob)
            if oob>30: res['fail'].append([n,'상자 밖 바뀜(남음)',oob])
            # 남은 조각: 상자 안에서 기준엔 있고 지금도 남아 있는데, 흔드는 팔 쪽 덩어리와 안 붙은 옷 조각
            only=(A&box)&~ndimage.binary_dilation(ref[...,3]>128,iterations=1)
            lb,k=ndimage.label(only); sz=ndimage.sum(only,lb,range(1,k+1)) if k else []
            big=max(sz) if len(sz) else 0
            ghost=(ref[...,3]>128)&A&box&d  # 팔이 비켜 간 자리에 옛 그림이 남으면 d 가 큼(정상)… 대신 실루엣 덩어리로 판단
            orphan=0
            lbA,kA=ndimage.label(A&box)
            if kA>1:
                szA=ndimage.sum(A&box,lbA,range(1,kA+1)); orphan=int(sorted(szA)[-2]) if kA>1 else 0
            lbR,kR=ndimage.label((ref[...,3]>128)&box); szR=ndimage.sum((ref[...,3]>128)&box,lbR,range(1,kR+1)) if kR else []
            orphanR=int(sorted(szR)[-2]) if kR>1 else 0
            orph=max(0,orphan-orphanR); st['max_orphan']=max(st['max_orphan'],orph)
            if orph>40: res['fail'].append([n,'떨어진 조각',orph])
    res['stats'][tag]=st
res['pass']=not res['fail']
json.dump(res,open(OUTJ,'w'),ensure_ascii=False,indent=1,default=float)
print(json.dumps({'frames':res['frames'],'pass':res['pass'],'fails':len(res['fail']),'first':res['fail'][:8],'stats':res['stats']},ensure_ascii=False,default=float))
