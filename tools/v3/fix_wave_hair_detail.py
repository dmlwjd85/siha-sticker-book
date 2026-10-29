"""흔들기용 뒷머리(hair_back_wave) 겨드랑이 아래 마무리. fix_wave_hair_streak 다음, sync_wave_parts 앞에 실행.
1) 팔 안쪽-머리 외곽선 만나는 곳(x1180~1250, y1460~1565)의 작은 구멍(투명)과 떨어진 어두운 부스러기를 머리색으로 메움
2) 주 외곽선 옆 가는 점선(x1180~1232, y1688~1798): 큰 선과 안 붙은 작은 어두운 조각을 지움
3) 메운 자리(밋밋한 단색)에 주변과 같은 머리결 선(어두운 결 2줄 + 밝은 결 1줄)을 가늘고 끝이 가늘어지게 그림
좌표는 2배 파츠 좌표."""
import sys, numpy as np, cv2
from scipy import ndimage
from PIL import Image
p = f'{sys.argv[1]}/hair_back_wave.png'; A = np.array(Image.open(p).convert('RGBA'))
def nearest_hair_fill(r, m):
    c = r[..., :3].astype(int)
    hair = (r[..., 3] > 200) & (c.sum(-1) > 450) & ((c[..., 0] - c[..., 1]) >= 55) & ~m
    _, (iy, ix) = ndimage.distance_transform_edt(~hair, return_indices=True)
    f = cv2.GaussianBlur(r[..., :3][iy, ix].astype(np.float32), (0, 0), 2)
    r[..., :3][m] = f[m].astype(np.uint8); r[..., 3][m] = 255
def clean(x0, x1, y0, y1, holes, minkeep=400):
    r = A[y0:y1, x0:x1]; c = r[..., :3].astype(int)
    dk = (r[..., 3] > 100) & (c.sum(-1) < 450)
    lb, n = ndimage.label(dk); sz = ndimage.sum(dk, lb, range(1, n + 1))
    keep = np.zeros(n + 1, bool); keep[1:] = sz >= minkeep   # 큰 선만 남김(머리 다발 끝 선은 남김)
    m = dk & ~keep[lb]
    if holes:
        tr = r[..., 3] < 200; lt, k = ndimage.label(tr)
        for i in range(1, k + 1):
            mm = lt == i
            ys, xs = np.where(mm)
            if mm.sum() < 300 and ys.min() > 0 and xs.min() > 0 and ys.max() < r.shape[0]-1 and xs.max() < r.shape[1]-1: m |= mm
    m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~(dk & keep[lb])
    nearest_hair_fill(r, m); return int(m.sum())
print('armpit', clean(1180, 1250, 1460, 1565, True, 40))
# 1b) 겨드랑이 흰 틈·회색 획(채도 낮은 비-선 픽셀) → 머리색, 선 덩어리 안 바늘구멍 → 선 색
r = A[1455:1560, 1190:1245]; c = r[..., :3].astype(int)
gap = (r[..., 3] > 0) & (c.sum(-1) >= 250) & ((c[..., 0] - c[..., 1]) < 38)
gap = cv2.dilate(gap.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & (c.sum(-1) >= 250) & ((c[..., 0] - c[..., 1]) < 45)
nearest_hair_fill(r, gap); print('gap', int(gap.sum()))
r = A[1470:1560, 1215:1250]; c = r[..., :3].astype(int)
ln = (r[..., 3] > 200) & (c.sum(-1) < 330)
pin = ~ln & ndimage.binary_fill_holes(cv2.dilate(ln.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)) & ~ndimage.binary_dilation(~ndimage.binary_fill_holes(ln), iterations=0)
pin &= ndimage.binary_fill_holes(ln)
r[..., :3][pin] = np.median(r[..., :3][ln], 0).astype(np.uint8); r[..., 3][pin] = 255; print('pin', int(pin.sum()))
# 1c) 남은 흰 획·회색 점선(작은 비-머리색 조각)
r = A[1525:1558, 1188:1228]; c = r[..., :3].astype(int)
dk = (r[..., 3] > 100) & (c.sum(-1) < 330); lb, n = ndimage.label(cv2.dilate(dk.astype(np.uint8), np.ones((3, 3), np.uint8)))
big = np.isin(lb, [i for i in range(1, n + 1) if (dk & (lb == i)).sum() >= 40])
odd = (r[..., 3] > 0) & ((c[..., 0] - c[..., 1]) < 55) & ~big
nearest_hair_fill(r, odd); print('odd', int(odd.sum()))
print('dotted', clean(1180, 1232, 1688, 1798, False))
# 3) 머리결
H, W = A.shape[:2]; S = 4
def strand(pts, col, wmax, alpha):
    lay = np.zeros((H * 0 + 400 * S, 160 * S), np.float32); ox, oy = 1150, 1540
    pts = np.array(pts, float); t = np.linspace(0, 1, 120)
    # 2차 베지어(3점)
    P = ((1 - t) ** 2)[:, None] * pts[0] + (2 * (1 - t) * t)[:, None] * pts[1] + (t ** 2)[:, None] * pts[2]
    for i in range(len(P) - 1):
        w = wmax * np.sin(np.pi * (i / (len(P) - 1)) * 0.98 + 0.01)   # 끝이 가늘게
        a = ((P[i] - [ox, oy]) * S).astype(int); b = ((P[i + 1] - [ox, oy]) * S).astype(int)
        cv2.line(lay, tuple(a), tuple(b), 1.0, max(1, int(w * S)), cv2.LINE_AA)
    lay = cv2.resize(lay, (160, 400), interpolation=cv2.INTER_AREA) * alpha
    reg = A[oy:oy + 400, ox:ox + 160]; ok = (reg[..., 3] > 200) & (reg[..., :3].astype(int).sum(-1) > 450)
    lay *= ok
    reg[..., :3] = (reg[..., :3] * (1 - lay[..., None]) + np.array(col) * lay[..., None]).astype(np.uint8)
strand([(1196, 1566), (1206, 1625), (1214, 1700)], (214, 126, 144), 2.2, 0.55)
strand([(1222, 1560), (1230, 1630), (1236, 1720)], (218, 130, 147), 1.8, 0.45)
strand([(1208, 1575), (1218, 1630), (1224, 1690)], (248, 182, 192), 2.6, 0.5)
Image.fromarray(A).save(p)
