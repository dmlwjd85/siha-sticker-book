"""흔들기 상의 왼쪽 위 소매선 끝·겨드랑이 마무리(basic_upper_wave, body_upper_wave). sync_wave_parts 앞뒤 무관(웨이브 파츠만 수정).
1) 소매선 끝이 두 갈래(본선 옆 1px 곁선 + 뭉툭한 덩어리) → 곁선 지우고 끝을 한 줄로 가늘게(테이퍼)
2) 본선과 안 붙은 짧은 사선 조각 → 주변 색으로 지움
3) 겨드랑이 V 꼭짓점 틈(머리 밝은 점이 비침) → 선 색으로 메움
4) 아래쪽 외곽선 옆 작은 가시/바늘구멍 정리
사용: python3 fix_sleeve_wave.py PARTS_DIR"""
import sys, numpy as np, cv2
from scipy import ndimage
from PIL import Image
D = sys.argv[1]
def load(n): return np.array(Image.open(f'{D}/{n}.png').convert('RGBA'))
def nonline_fill(r, m):
    c = r[..., :3].astype(int)
    far = ndimage.distance_transform_edt(~darkm(r)) > 10
    ref = np.median(c[far & (r[..., 3] > 250)], 0)
    good = (r[..., 3] > 250) & (np.abs(c - ref).max(-1) < 40) & ~lineish(r) & ~cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    _, (iy, ix) = ndimage.distance_transform_edt(~good, return_indices=True)
    f = cv2.GaussianBlur(r[..., :3][iy, ix].astype(np.float32), (0, 0), 2.0)
    r[..., :3][m] = f[m].astype(np.uint8)
def lineish(r):
    c = r[..., :3].astype(int); return (c.sum(-1) < 450) | (c[..., 2] >= c[..., 1] - 8)
def darkm(r): return (r[..., 3] > 128) & (r[..., :3].astype(int).sum(-1) < 450)
def taper_top(A, box, L, YC=12):
    """box 안 세로선: 각 행 가장 긴 어두운 구간만 본선으로, 위 끝 L행은 폭을 sqrt로 줄여 뾰족하게. 나머지 어두운 픽셀은 지움."""
    x0, y0, x1, y1 = box; r = A[y0:y1, x0:x1]; dk = darkm(r)
    col = np.median(r[..., :3][dk & (r[..., :3].astype(int).sum(-1) < 260)], 0)
    rows = [y for y in range(dk.shape[0]) if dk[y].any()]; top = rows[0]
    runs = {}
    for y in rows:
        lb, n = ndimage.label(dk[y]); sz = ndimage.sum(dk[y], lb, range(1, n + 1)); i = int(np.argmax(sz)) + 1
        xs = np.where(lb == i)[0]; runs[y] = (xs.mean(), len(xs))
    wref = np.median([runs[y][1] for y in rows if y > top + L][:20])
    cref = np.mean([runs[y][0] for y in rows if top + L < y <= top + L + 8])
    # 중심선을 4행 간격 점으로 잡고, 위 끝은 폭을 줄여가며 원을 이어 찍어(8배 해상도) 한 줄로 다시 그림
    base = [y for y in rows if y >= top + L]
    yc = top + L + YC; base = [y for y in base if y <= yc + 2]
    pts = [(np.mean([runs[q][0] for q in base if abs(q - y) <= 2]), y, np.mean([runs[q][1] for q in base if abs(q - y) <= 2])) for y in base[::2]]
    wref = pts[0][2]
    tipx = cref; tipy = top + 2
    for k in range(L, 0, -1):
        t = k / L; y = top + L - k * (L - 2) / L
        pts.insert(0, (cref, top + L - (L - 2) * t, wref * np.sqrt(max(1 - t, 0.04)) * 0.95))
    S = 8; lay = np.zeros((dk.shape[0] * S, dk.shape[1] * S), np.float32)
    for (xa, ya, wa), (xb, yb, wb) in zip(pts[:-1], pts[1:]):
        for u in np.linspace(0, 1, 6):
            x = xa + (xb - xa) * u; y = ya + (yb - ya) * u; w = wa + (wb - wa) * u
            cv2.circle(lay, (int((x + .5) * S), int((y + .5) * S)), max(1, int(w / 2 * S)), 1.0, -1, cv2.LINE_AA)
    lay = cv2.resize(lay, dk.shape[::-1], interpolation=cv2.INTER_AREA)
    old = (cv2.dilate(dk.astype(np.uint8), np.ones((11, 11), np.uint8)) > 0) & (r[..., 3] > 0)
    old[yc:] = False; lay[yc:] = 0
    nonline_fill(r, old)
    c2 = r[..., :3].astype(int); stray = (r[..., 3] > 0) & (lay < 0.05) & ((c2.sum(-1) < 600) | (c2[..., 2] >= c2[..., 1] - 25))
    stray[top + L + 4:] = False
    nonline_fill(r, cv2.dilate(stray.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & (lay < 0.05))
    r[..., :3] = (r[..., :3] * (1 - lay[..., None]) + col * lay[..., None]).astype(np.uint8)
    return int(old.sum())
def erase_frag(A, box):
    x0, y0, x1, y1 = box; r = A[y0:y1, x0:x1]; dk = darkm(r)
    m = cv2.dilate(dk.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool) & (r[..., 3] > 0)
    nonline_fill(r, m); return int(m.sum())
def close_apex(A, box, k=7):
    x0, y0, x1, y1 = box; r = A[y0:y1, x0:x1]; dk = darkm(r)
    col = np.median(r[..., :3][dk & (r[..., :3].astype(int).sum(-1) < 260)], 0)
    cl = cv2.morphologyEx(dk.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))).astype(bool)
    m = cl & ~dk; r[..., :3][m] = col.astype(np.uint8); r[..., 3][m] = 255; return int(m.sum())
def despur(A, box, k=5):
    x0, y0, x1, y1 = box; r = A[y0:y1, x0:x1]; dk = darkm(r)
    op = cv2.morphologyEx(dk.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))).astype(bool)
    op = cv2.dilate(op.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & dk
    m = dk & ~op & (r[..., 3] > 250)
    m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~op & (r[..., 3] > 250)
    nonline_fill(r, m); return int(m.sum())
# basic_upper_wave (부착 478,678)
A = load('basic_upper_wave')
print('basic frag', erase_frag(A, (834, 120, 866, 262)))
print('basic taper', taper_top(A, (798, 190, 834, 320), 22, 48))
print('basic apex', close_apex(A, (800, 375, 870, 425)))
print('basic spur', despur(A, (760, 600, 810, 700)))
Image.fromarray(A).save(f'{D}/basic_upper_wave.png')
# body_upper_wave (부착 389,121): 같은 자리 = basic 좌표 + (178, 1114)
A = load('body_upper_wave')
print('body taper', taper_top(A, (976, 1330, 1012, 1394), 18))
Image.fromarray(A).save(f'{D}/body_upper_wave.png')
