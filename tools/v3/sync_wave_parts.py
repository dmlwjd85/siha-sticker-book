"""손 흔들기용 *_wave 파츠를 기본 파츠와 같은 처리 결과로 맞춘다.
흔들기 상자(changeBox, 안쪽으로 16px 줄임) 밖의 픽셀은 기본 파츠에서 그대로 복사 → 흔들 때 상자 밖이 바뀌지 않음.
파이프라인: 모든 파츠 정리(smooth_outlines·clean_white_tint·fix_thigh_tick 등)를 마친 뒤 맨 마지막에 실행."""
import sys, json, numpy as np
from PIL import Image
d = sys.argv[1]; sk = json.load(open(f'{d}/../skeleton.json'))
x0, y0, x1, y1 = sk['animations']['wave']['changeBox']; M = 16
x0 += M; y0 += M; x1 -= M; y1 -= M
att = {}
for slot in sk['skins'].values() if isinstance(sk['skins'], dict) else []:
    pass
def find(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, dict) and 'path' in v and 'x' in v: att[k] = v
            else: find(v)
    elif isinstance(o, list):
        for v in o: find(v)
find(sk)
for w, a in att.items():
    b = w.replace('_wave', '')
    if not w.endswith('_wave') or b not in att: continue
    A = np.array(Image.open(f'{d}/{w}.png').convert('RGBA')); B = np.array(Image.open(f'{d}/{b}.png').convert('RGBA'))
    sx, sy = a['x'], a['y']; assert (att[b]['x'], att[b]['y']) == (sx, sy)
    h = min(A.shape[0], B.shape[0]); wd = min(A.shape[1], B.shape[1])
    ys = np.arange(h)[:, None] / 2 + sy; xs = np.arange(wd)[None, :] / 2 + sx
    out = ~((xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1))
    k = int((out & (A[:h, :wd] != B[:h, :wd]).any(-1)).sum())
    A[:h, :wd][out] = B[:h, :wd][out]
    Image.fromarray(A).save(f'{d}/{w}.png'); print(w, k)
