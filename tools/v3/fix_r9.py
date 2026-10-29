"""Round 9: redraw the straight centre hair line on hair_back_wave as a natural curve,
clean red diagonal / dark smudges near the armpit. Run after fix_wave_hair_detail.py."""
import sys, numpy as np, cv2
from PIL import Image
P = sys.argv[1]; p = P + '/hair_back_wave.png'
A = np.array(Image.open(p).convert('RGBA'))
c = A[..., :3].astype(int); s = c.sum(-1)
H, W = s.shape
yy, xx = np.mgrid[0:H, 0:W]
# 1) erase straight line (1158,1580)->(1238,1890): row-wise, interpolate between side refs
x0, y0, x1, y1 = 1157, 1568, 1239, 1892
m = np.zeros((H, W), bool)
for y in range(y0, y1 - 3):
    lx = x0 + (y - y0) * (x1 - x0) / (y1 - y0); xc = int(round(lx))
    # recentre on darkest pixel nearby
    xc = xc - 4 + int(np.argmin(s[y, xc - 4:xc + 5]))
    a, b = xc - 6, xc + 6
    if A[y, a, 3] < 200 or A[y, b, 3] < 200: continue
    ca, cb = A[y, a, :3].astype(float), A[y, b, :3].astype(float)
    for x in range(a + 1, b):
        u = (x - a) / (b - a); A[y, x, :3] = (ca * (1 - u) + cb * u).astype(np.uint8); m[y, x] = True
s = A[..., :3].astype(int).sum(-1)
# 2) red diagonal + dark smudges: boxes
def box(x0, y0, x1, y1):
    b = np.zeros_like(m); b[y0:y1, x0:x1] = True; return b
sm = (box(1140, 1598, 1180, 1632) & (s < 560) & (s > 200)) | (box(1162, 1622, 1200, 1660) & (s < 540)) \
     | (box(1205, 1780, 1250, 1860) & (s < 520))
m2 = sm & (A[..., 3] > 200); m = m2
good = (A[..., 3] > 200) & ~m & (s > 380)
# exclude outlines from source
good &= s > 420
num = np.zeros((H, W, 3), np.float32); den = np.zeros((H, W), np.float32)
for sg in (2, 4, 8):
    w = cv2.GaussianBlur(good.astype(np.float32), (0, 0), sg)
    n = cv2.GaussianBlur(A[..., :3].astype(np.float32) * good[..., None], (0, 0), sg)
    upd = (den < 0.05) & (w > 0.02)
    num[upd] = n[upd]; den[upd] = w[upd]
f = num / np.maximum(den, 1e-4)[..., None]
A[..., :3][m] = np.clip(f[m], 0, 255).astype(np.uint8)
print('erased', int(m.sum()))
# 2b) vertical (hair-flow) smoothing of leftover streaks / ticks before redrawing
from scipy import ndimage
for (bx0, by0, bx1, by1, dark_all) in [(1130, 1540, 1196, 1700, False), (1214, 1835, 1262, 1880, True)]:
    s = A[..., :3].astype(int).sum(-1)
    B = np.zeros((H, W), bool); B[by0:by1, bx0:bx1] = True
    dk = B & (s < (400 if dark_all else 500)) & (A[..., 3] > 200)
    if not dark_all:  # only small isolated ticks
        lab, n = ndimage.label(dk)
        sz = ndimage.sum(dk, lab, range(1, n + 1))
        dk = np.isin(lab, [i + 1 for i, z in enumerate(sz) if z < 40])
    dk = cv2.dilate(dk.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    src = (A[..., 3] > 200) & (s > 400) & ~dk
    wv = cv2.GaussianBlur(src.astype(np.float32), (0, 0), sigmaX=1.5, sigmaY=8)
    nv = cv2.GaussianBlur(A[..., :3].astype(np.float32) * src[..., None], (0, 0), sigmaX=1.5, sigmaY=8)
    fv = nv / np.maximum(wv, 1e-4)[..., None]
    # feathered weight: ramp 10 px at box borders
    ry = np.clip(np.minimum(yy - by0, by1 - yy) / 10, 0, 1); rx = np.clip(np.minimum(xx - bx0, bx1 - xx) / 6, 0, 1)
    wt = (ry * rx) * (src | dk); wt[dk] = 1
    wt = wt[..., None]
    A[..., :3] = np.clip(A[..., :3] * (1 - wt) + fv * wt, 0, 255).astype(np.uint8)
# 2c) leftover triangle edge + tick (targeted)
s = A[..., :3].astype(int).sum(-1)
dk = np.zeros((H, W), bool)
for (bx0, by0, bx1, by1) in [(1142, 1596, 1155, 1651), (1148, 1584, 1162, 1600)]:
    dk[by0:by1, bx0:bx1] = True
dk &= (s < 540) & (A[..., 3] > 200)
dk = cv2.dilate(dk.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
src = (A[..., 3] > 200) & (s > 450) & ~dk
wv = cv2.GaussianBlur(src.astype(np.float32), (0, 0), sigmaX=2, sigmaY=8)
nv = cv2.GaussianBlur(A[..., :3].astype(np.float32) * src[..., None], (0, 0), sigmaX=2, sigmaY=8)
A[..., :3][dk] = np.clip((nv / np.maximum(wv, 1e-4)[..., None])[dk], 0, 255).astype(np.uint8)
# 3) redraw as curve following hair flow (gentle S), slight taper, joins at both ends
S = 4; ox, oy, bw, bh = 1100, 1540, 200, 380
lay = np.zeros((bh * S, bw * S), np.float32)
pts = np.array([(1158, 1574), (1146, 1690), (1222, 1770), (1238, 1892)], float)
t = np.linspace(0, 1, 400)
Q = (((1 - t) ** 3)[:, None] * pts[0] + (3 * (1 - t) ** 2 * t)[:, None] * pts[1]
     + (3 * (1 - t) * t ** 2)[:, None] * pts[2] + (t ** 3)[:, None] * pts[3])
for i, q in enumerate(Q):
    u = i / (len(Q) - 1)
    w = 1.2 + 1.6 * np.sin(np.pi * u) ** 0.8   # thicker in the middle, thinner at the joins
    cv2.circle(lay, tuple(((q - [ox, oy]) * S).astype(int)), max(1, int(w * S / 2)), 1.0, -1, cv2.LINE_AA)
lay = cv2.resize(lay, (bw, bh), interpolation=cv2.INTER_AREA)
reg = A[oy:oy + bh, ox:ox + bw]; lay *= reg[..., 3] > 200
col = np.array((52, 26, 36), float)
reg[..., :3] = (reg[..., :3] * (1 - lay[..., None]) + col * lay[..., None]).astype(np.uint8)
Image.fromarray(A).save(p)
