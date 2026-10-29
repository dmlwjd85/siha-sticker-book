"""Round 9: side-hair tie loops. Smooth the tone edge at the end of the right-loop fade and
let the tie strings run into the knot with tapered ends (no blunt stubs). Run after fix_side_hair.py."""
import sys, numpy as np, cv2
from PIL import Image
P = sys.argv[1]
def smooth_light(A, box, sg=7, feather=8):
    x0, y0, x1, y1 = box; H, W = A.shape[:2]
    s = A[..., :3].astype(int).sum(-1)
    src = (A[..., 3] > 250) & (s > 600)
    srcd = cv2.erode(src.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    w = cv2.GaussianBlur(srcd.astype(np.float32), (0, 0), sg)
    n = cv2.GaussianBlur(A[..., :3].astype(np.float32) * srcd[..., None], (0, 0), sg)
    f = n / np.maximum(w, 1e-4)[..., None]
    yy, xx = np.mgrid[0:H, 0:W]
    ry = np.clip(np.minimum(yy - y0, y1 - yy) / feather, 0, 1); rx = np.clip(np.minimum(xx - x0, x1 - xx) / feather, 0, 1)
    wt = (ry * rx * srcd)
    wt = cv2.GaussianBlur(wt.astype(np.float32), (0, 0), 1.0) * src
    A[..., :3] = np.clip(A[..., :3] * (1 - wt[..., None]) + f * wt[..., None], 0, 255).astype(np.uint8)
def tapered(A, p0, p1, w0, w1, col):
    S = 4; x0 = int(min(p0[0], p1[0])) - 6; y0 = int(min(p0[1], p1[1])) - 6
    bw = int(abs(p1[0] - p0[0])) + 13; bh = int(abs(p1[1] - p0[1])) + 13
    lay = np.zeros((bh * S, bw * S), np.float32)
    for t in np.linspace(0, 1, 60):
        q = (np.array(p0) * (1 - t) + np.array(p1) * t - [x0, y0]) * S
        cv2.circle(lay, tuple(q.astype(int)), max(1, int((w0 * (1 - t) + w1 * t) * S / 2)), 1.0, -1, cv2.LINE_AA)
    lay = cv2.resize(lay, (bw, bh), interpolation=cv2.INTER_AREA)
    reg = A[y0:y0 + bh, x0:x0 + bw]
    reg[..., :3] = (reg[..., :3] * (1 - lay[..., None]) + np.array(col) * lay[..., None]).astype(np.uint8)
    reg[..., 3] = np.maximum(reg[..., 3], (lay * 255).astype(np.uint8))
# string end -> knot stub top (hair_back px). width tapers from string width into stub width
JOIN = [((1339, 823), (1343.5, 833), 1.6, 2.6), ((1351, 822), (1350.5, 833), 1.6, 2.6),
        ((290.5, 833), (288, 842), 2.6, 3.4), ((309.5, 836), (305.5, 846), 3.0, 3.4)]
for name in ['hair_back', 'hair_back_wave']:
    A = np.array(Image.open(f'{P}/{name}.png').convert('RGBA'))
    smooth_light(A, (1312, 800, 1400, 900))
    smooth_light(A, (1325, 900, 1375, 960), sg=4, feather=5)
    smooth_light(A, (278, 808, 332, 905))
    s = A[..., :3].astype(int).sum(-1)
    for (a, b, w0, w1) in JOIN:
        # line colour sampled from knot stub
        xs, ys = int(b[0]), int(b[1]) + 2
        reg = A[ys - 3:ys + 4, xs - 3:xs + 4, :3].reshape(-1, 3).astype(int)
        col = reg[reg.sum(1).argmin()]
        tapered(A, a, b, w0, w1, col.tolist())
    # knot stub tidy: remove blunt nubs / faint bridges, close the notch in the left string
    s = A[..., :3].astype(int).sum(-1)
    for (x0, y0, x1, y1) in [(291, 837, 296, 842), (1343, 828, 1350, 831)]:
        sub = A[y0 - 4:y1 + 4, x0 - 4:x1 + 4, :3]; ss = s[y0 - 4:y1 + 4, x0 - 4:x1 + 4]
        lt = sub[ss > 560].reshape(-1, 3)
        if len(lt) == 0: continue
        hc = np.median(lt, 0)
        m = np.zeros(ss.shape, bool); m[4:-4, 4:-4] = ss[4:-4, 4:-4] > 300
        sub[m] = hc
    x0, y0, x1, y1 = 302, 838, 313, 846
    d = (s[y0:y1, x0:x1] < 420).astype(np.uint8)
    cl = cv2.morphologyEx(d, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    add_ = (cl > d); col = A[y0:y1, x0:x1, :3][d.astype(bool)].reshape(-1, 3).min(0) + 20
    A[y0:y1, x0:x1, :3][add_] = col
    lab, n = __import__('scipy.ndimage', fromlist=['label']).label(cl)
    Image.fromarray(A).save(f'{P}/{name}.png')
print('loops r9 ok')
