"""뒷머리(hair_back*) 어깨 옆 머리카락 고리 안쪽의 투명 구멍(흰 빈틈)을 메운다.
가장자리에 닿지 않는 닫힌 투명 구멍 중 어깨 높이(skel y 700~800, 몸통 바깥) 것만 대상.
구멍+윤곽선을 마스크로 잡아 주변 머리색(평평한 셀 색)으로 채운다. 팔꿈치 아래 물방울 틈도 포함. 사용: python3 fill_hair_holes.py PARTS_DIR
"""
import sys, numpy as np, cv2
from PIL import Image
d = sys.argv[1]
for n in ['hair_back', 'hair_back_wave']:
    p = f'{d}/{n}.png'; a = np.array(Image.open(p).convert('RGBA'))
    t = (a[..., 3] < 128).astype(np.uint8)
    k, lab, st, _ = cv2.connectedComponentsWithStats(t, connectivity=4)
    H, W = t.shape
    m = np.zeros_like(t); other = np.zeros_like(t)
    for i in range(1, k):
        x, y, w, h, ar = st[i]
        sx, sy = x / 2 + 303, y / 2 + 102
        if x > 0 and y > 0 and x + w < W and y + h < H and ar > 30 and ((700 <= sy <= 800 and (sx < 400 or sx > 1000)) or (980 <= sy <= 1060 and 480 <= sx <= 540)):
            m |= (lab == i).astype(np.uint8)
        elif x > 0 and y > 0 and x + w < W and y + h < H and ar > 30:
            other |= (lab == i).astype(np.uint8)
    # 구멍 끝의 가는 흰 틈까지 포함: 밝은 무채색 픽셀을 구멍에 붙인다
    rgb = a[..., :3].astype(int)
    whiteish = (rgb.min(-1) > 190) & (rgb.max(-1) - rgb.min(-1) < 40)
    near = cv2.dilate(m, np.ones((81, 81), np.uint8))
    m |= (whiteish & (near > 0)).astype(np.uint8)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19)))
    # 바깥 실루엣 윤곽선(외부 투명 영역에서 12px 이내)은 건드리지 않는다
    outside = np.zeros_like(t)
    for i in range(1, k):
        x, y, w, h, ar = st[i]
        if x == 0 or y == 0 or x + w == W or y + h == H: outside |= (lab == i).astype(np.uint8)
    m &= (cv2.dilate(outside, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))) == 0).astype(np.uint8)
    # 셀 채색이므로 평평한 머리색으로 채운다(블러·얼룩 금지). 구멍마다 주변 링의 최빈색(선 제외)
    kk, ml = cv2.connectedComponents(m)
    full = np.zeros(m.shape, np.float32); fill = np.zeros(a.shape[:2] + (3,), np.float32)
    for j in range(1, kk):
        mj = (ml == j).astype(np.uint8)
        ring = (cv2.dilate(mj, np.ones((15, 15), np.uint8)) > 0) & (mj == 0) & (a[..., 3] > 250) & (rgb.sum(-1) > 450)
        q = (rgb[ring] // 6) * 6
        vals, cnt = np.unique(q, axis=0, return_counts=True)
        fill[mj > 0] = vals[cnt.argmax()] + 3
    soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.8)
    fillb = cv2.dilate(fill, np.ones((5, 5), np.uint8))
    for c in range(3):
        a[..., c] = (a[..., c] * (1 - soft) + fillb[..., c] * soft).astype(np.uint8)
    a[m > 0, 3] = 255
    # 남겨 두는 머리카락 사이 틈: 끝부분의 회색·흰 조각은 투명으로(틈 자체는 자연스러운 머리결)
    rgb2 = a[..., :3].astype(int)
    grey = (rgb2.min(-1) > 150) & (rgb2.max(-1) - rgb2.min(-1) < 30) & (a[..., 3] > 0)
    a[grey & (cv2.dilate(other, np.ones((31, 31), np.uint8)) > 0), 3] = 0
    Image.fromarray(a).save(p); print('filled', n, int(m.sum()))
