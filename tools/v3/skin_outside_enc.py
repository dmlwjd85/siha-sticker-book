"""check_skin_outside 용 '층 색칠' 사이트 만들기.
dist/ 를 통째로 복사한 뒤, 복사본의 v3-demo/parts 에서
  몸(body_*)  → 살·밝은 부분 순수 파랑(0,0,255), 진한 외곽선 어두운 파랑(0,0,140)
  옷(basic_*, 흔드는 팔 옷 포함) → 순수 빨강(255,0,0)
  그 밖의 층(팔 아래·손·눈·소품) → 초록(0,160,0)
  hair_*  → 원래 색 그대로(머리 뒤 층에 구워진 흰/살색 몸통 조각을 찾으려고)
으로 칠한다. 원본 dist/ 와 public/ 은 건드리지 않는다.
사용: python3 tools/v3/skin_outside_enc.py <dist 폴더> <출력 루트>   (예: dist /tmp/encroot)
그 뒤: python3 -m http.server 4181 -d /tmp/encroot  → http://localhost:4181/siha-sticker-book/v3-demo/"""
import sys,shutil,os,glob,numpy as np
from PIL import Image
src,root=sys.argv[1],sys.argv[2]
dst=os.path.join(root,'siha-sticker-book'); shutil.rmtree(root,ignore_errors=True); shutil.copytree(src,dst)
for f in glob.glob(os.path.join(dst,'v3-demo/parts/*.png')):
    n=os.path.basename(f)
    if n.startswith('body_'): col=(0,0,255)
    elif n.startswith('basic_'): col=(255,0,0)
    elif n.startswith('hair_'): continue
    else: col=(0,160,0)   # 팔 아래·손·얼굴·소품 등 다른 층 = 초록(살색으로 오인하지 않게)
    a=np.array(Image.open(f).convert('RGBA')); dark=a[...,:3].astype(int).sum(-1)<420
    a[...,:3]=col; a[...,3]=np.where(a[...,3]>0,255,0)
    if col==(0,0,255): a[...,:3][dark]=(0,0,140)   # 몸의 진한 외곽선 = 어두운 파랑(살 아님)
    Image.fromarray(a).save(f)
print('ok',dst)
