"""몸이 옷 바깥 외곽선 밖으로 삐져나오는지 전 프레임 검사 (Round 14, 2026-10-29).
입력: skin_outside_enc.py 로 만든 '층 색칠' 사이트를 check_frames.mjs 로 찍은 프레임 폴더.
  몸=파랑, 옷=빨강, 나머지 층(팔 아래·머리·얼굴·소품)은 원래 색.
검사(프레임마다, 0건이어야 통과):
 A) 몸 삐져나옴(옷 입은 프레임): 옷(빨강) 실루엣 밖에 있는 몸(파랑) 덩어리 중, 옷에서 가장 먼 점이 30px 이하이고 살(밝은 파랑)이 6px 이상인 것
    (몸 외곽선만 옷 외곽선 옆에 겹쳐 보이는 1~2px 선은 살이 아니라서 제외)
    = 옷 옆으로 삐져나온 몸(특히 허리 양옆). 팔·다리·목처럼 옷에서 멀리 뻗는 덩어리는 제외. 어깨 아래(윗옷 맨 윗줄+60)~치마 아랫단만.
 B) 머리 뒤 층에 구워진 몸통(모든 프레임): 몸/옷 실루엣 바깥 4~40px 띠에 보이는 흰/살색(채도 낮은 밝은색, 머리 분홍 아님) 덩어리
    중 면적 20px 이상 = 옛 몸 옆선이 머리 뒤 층에서 비쳐 보이는 것. (얼굴·팔·손·소품은 다른 층이라 실루엣 띠 계산에서 뺌: 몸통 띠 줄만 봄)
사용: python3 tools/v3/check_skin_outside.py <프레임 폴더> [보고서.json]"""
import sys,json,numpy as np
from PIL import Image
from scipy import ndimage as nd
D=sys.argv[1]; OUT=sys.argv[2] if len(sys.argv)>2 else D+'/skin_outside.json'
L=json.load(open(D+'/frames.json'))
def masks(im):
    r,g,b,a=[im[...,i].astype(int) for i in range(4)]
    blue=(b>110)&(r<60)&(g<60)&(a>200); skin=(b>200)&(r<60)&(g<60)&(a>200); red=(r>200)&(g<60)&(b<60)&(a>200)
    return blue,red,r,g,b,a,skin
res=[];tot=0
for f in L:
    im=np.array(Image.open(f"{D}/{f['name']}.png").convert('RGBA'))
    blue,red,r,g,b,a,skin=masks(im); H,W=blue.shape; A_hits=[];B_hits=0
    # 몸통 띠: 파랑 덩어리 가운데 열 근처 줄 범위
    ys,xs=np.where(blue|red)
    if len(ys)==0: res.append({'name':f['name'],'A':0,'B':0}); continue
    if f['outfit']=='basic' and red.any():
        # 몸통 띠 위끝 = 몸 중심 열에서 옷(빨강)이 시작되는 줄. (흔들기 프레임에서 든 팔 소매가 얼굴 높이까지 올라가 띠에 얼굴이 들어가지 않게)
        bx=int(np.median(np.where(blue)[1])); cy=np.where(red[:,max(0,bx-3):bx+4].any(1))[0]
        top=int(cy.min()) if len(cy) else int(np.where(red.any(1))[0].min()); 
        # 치마 아랫단: 빨강의 아래 경계(신발 위 다리 구간은 빨강이 끊김) – 몸통 중심 열에서 빨강이 끝나는 줄
        cx=int(np.median(np.where(red[top+40])[0])) if red[top+40].any() else int(xs.mean())
        col=red[:,cx]; bot=top+40
        while bot<H-1 and (col[bot+1] or col[min(bot+4,H-1)]): bot+=1
        # 옷 밖 몸 조각: 옷 실루엣(빨강+1px 안티앨리어싱) 밖의 파랑 덩어리 중
        #  옷에서 가장 먼 점이 30px 이하(=옷 옆에 붙은 얇은 띠)인 것. 팔·다리·목은 옷에서 멀리 뻗어 나가 제외됨.
        G=nd.binary_dilation(red,iterations=2)
        out=blue&~G; out[:top+60]=False; out[bot+1:]=False
        dist=nd.distance_transform_edt(~G)
        allout=blue&~G
        lb,n=nd.label(allout)
        for k,sl in enumerate(nd.find_objects(lb),1):
            m=lb[sl]==k
            if not (out[sl]&m).any(): continue
            if dist[sl][m].max()<=30 and (skin[sl]&m).sum()>=6:
                A_hits.append([int(sl[0].start),int(sl[1].start),int(m.sum())])
        band=(top,bot)
    else:
        by=np.where(blue.any(1))[0]; band=(by.min()+int(0.22*(by.max()-by.min())),by.min()+int(0.55*(by.max()-by.min())))
    # B) 실루엣 바깥 띠의 흰/살색
    S=blue|red; ring=nd.binary_dilation(S,iterations=40)&~nd.binary_dilation(S,iterations=4)
    ring[:band[0]]=False; ring[band[1]:]=False
    pale=(a>200)&(r>200)&(g>185)&(b>180)&(r-g<35)&~blue&~red
    lb,n=nd.label(pale&ring); sz=nd.sum(pale&ring,lb,range(1,n+1)) if n else []
    B_hits=int(sum(1 for v in sz if v>=20))
    res.append({'name':f['name'],'A':len(A_hits),'Ahits':A_hits[:5],'B':B_hits}); tot+=len(A_hits)+B_hits
bad=[x for x in res if x['A'] or x['B']]
rep={'frames':len(res),'bad_frames':len(bad),'total':tot,'bad':bad[:40]}
json.dump(rep,open(OUT,'w'),ensure_ascii=False,indent=1)
print(json.dumps({k:rep[k] for k in ('frames','bad_frames','total')}))
sys.exit(1 if tot else 0)
