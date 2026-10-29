"""뒷머리 머리-얼굴 사이 닫힌 틈(흰 홈)을 머리 그림자색(평평한 셀 색)으로 메우고,
머리카락 끝의 고립된 작은 어두운 점을 주변 머리색으로 지운다. 사용: python3 fill_head_gaps.py PARTS_DIR"""
import sys, numpy as np, cv2
from PIL import Image
d = sys.argv[1]
OFF = {'hair_back': (303, 102), 'hair_back_wave': (303, 102)}
for n in ['hair_back', 'hair_back_wave']:
    p = f'{d}/{n}.png'; a = np.array(Image.open(p).convert('RGBA'))
    ox, oy = OFF[n]
    t = (a[..., 3] < 128).astype(np.uint8); H, W = t.shape
    k, lab, st, _ = cv2.connectedComponentsWithStats(t, connectivity=4)
    m = np.zeros_like(t)
    for i in range(1, k):
        x, y, w, h, ar = st[i]
        if x == 0 or y == 0 or x + w == W or y + h == H or ar < 20: continue
        cy = (y + h / 2) / 2 + oy
        if cy < 700: m |= (lab == i).astype(np.uint8)
    rgb = a[..., :3].astype(int)
    whiteish = (rgb.min(-1) > 185) & (rgb.max(-1) - rgb.min(-1) < 45) & (a[..., 3] > 0)
    m |= (whiteish & (cv2.dilate(m, np.ones((41, 41), np.uint8)) > 0)).astype(np.uint8)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    light = ((a[..., :3].astype(int).sum(-1) > 290) | (t > 0)).astype(np.uint8)
    m &= light  # 윤곽선(어두운 선)은 보존
    for _ in range(8):  # 선과 채움 사이에 남는 1~2px 밝은 띠까지 흡수(어두운 선은 넘지 않음)
        m = cv2.dilate(m, np.ones((3, 3), np.uint8)) & light
    kk, ml = cv2.connectedComponents(m)
    for j in range(1, kk):
        mj = ml == j
        ring = (cv2.dilate(mj.astype(np.uint8), np.ones((21, 21), np.uint8)) > 0) & ~mj & (a[..., 3] > 250) & (rgb.sum(-1) > 450)
        if ring.sum() == 0: continue
        rr = rgb[ring]; rr = rr[(rr[:, 0] - rr[:, 1] > 40)]  # 분홍 머리색만
        if len(rr) == 0: continue
        col = np.clip(np.median(rr, 0) * np.array([0.95, 0.88, 0.9]), 0, 255).astype(np.uint8)  # 그림자 톤
        a[mj, :3] = col; a[mj, 3] = 255
    # 고립된 어두운 점: 어두운 픽셀 연결요소 중 작은 것
    for nn in [n]:
        rgb = a[..., :3].astype(int)
        dark = ((rgb.sum(-1) < 330) & (a[..., 3] > 200)).astype(np.uint8)
        k2, l2, s2, _ = cv2.connectedComponentsWithStats(dark, connectivity=8)
        cnt = 0
        for i in range(1, k2):
            if s2[i, 4] <= 60:
                mi = l2 == i
                ring = (cv2.dilate(mi.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & ~mi & (a[..., 3] > 200)
                if ring.sum() < 4: continue
                a[mi, :3] = np.median(a[ring][:, :3], 0).astype(np.uint8); cnt += 1
    Image.fromarray(a).save(p); print(n, 'gap px', int(m.sum()), 'specks', cnt)
