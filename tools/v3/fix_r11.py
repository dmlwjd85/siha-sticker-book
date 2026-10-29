"""Round 11 QA fixes (wave parts). Usage: fix_r11.py PARTS_DIR"""
import sys, numpy as np, cv2
from PIL import Image
P = sys.argv[1]

def load(n): return np.array(Image.open(f'{P}/{n}.png').convert('RGBA')).astype(np.float32)
def save(n, A): Image.fromarray(np.clip(A + .5, 0, 255).astype(np.uint8)).save(f'{P}/{n}.png')

def refill(A, mask, srcmask, sig):
    C = A[..., :3]; s = srcmask.astype(np.float32)
    num = cv2.GaussianBlur(C * s[..., None], (0, 0), sig); den = cv2.GaussianBlur(s, (0, 0), sig)
    f = num / np.maximum(den, 1e-4)[..., None]
    m = mask[..., None]
    A[..., :3] = C * (1 - m) + f * m

def dot_split(A):
    s = A[..., :3].sum(2); H, W = s.shape
    yy, xx = np.mgrid[0:H, 0:W]
    lx = 1359 + (yy - 1695) * (8.0 / 34)
    box = (yy >= 1694) & (yy <= 1730) & (xx >= 1337) & (xx <= lx - 2.5)
    m = box & (s < 535)
    m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & box
    src = (s > 530) & (A[..., 3] > 250)
    src[:1660] = False; src[1745:] = False; src[:, :1320] = False; src[:, 1390:] = False
    refill(A, np.maximum(m.astype(np.float32), cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2) * box), src, 6)
    return int(m.sum())

U = 4
def ss(cov, sg):
    up = cv2.resize(cov, (cov.shape[1]*U, cov.shape[0]*U), interpolation=cv2.INTER_LINEAR) > 0.5
    sd = (cv2.distanceTransform(up.astype(np.uint8), cv2.DIST_L2, 5)
          - cv2.distanceTransform((~up).astype(np.uint8), cv2.DIST_L2, 5))
    sd = cv2.GaussianBlur(sd, (0, 0), sg*U)
    return cv2.resize(np.clip(sd/U + 0.5, 0, 1).astype(np.float32), (cov.shape[1], cov.shape[0]), interpolation=cv2.INTER_AREA)

def armpit_outline(A, x0, y0, x1, y1, sg=3.0):
    """re-draw the outline (ink band + alpha edge) as smooth curves inside the box"""
    sub = A[y0:y1, x0:x1].copy(); C = sub[..., :3]; al = sub[..., 3] / 255.; s = C.sum(2)
    inkm = (al > .9) & (s < 330); ink = np.median(C[inkm], 0)
    hairm = (al > .97) & (s > 430)
    hc = cv2.GaussianBlur(C * hairm[..., None], (0, 0), 4) / np.maximum(cv2.GaussianBlur(hairm.astype(np.float32), (0, 0), 4), 1e-4)[..., None]
    d = np.clip(((hc - C) * (hc - ink)).sum(2) / np.maximum(((hc - ink) ** 2).sum(2), 1), 0, 1)
    cov_body = ss(al.astype(np.float32), sg)            # silhouette (ink+hair)
    cov_hair = ss(((1 - d) * (al > .5)).astype(np.float32), sg) * cov_body  # hair inside ink
    # feather the edit into the box borders
    yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0]
    e = np.minimum.reduce([yy, xx, y1 - y0 - 1 - yy, x1 - x0 - 1 - xx]).astype(np.float32)
    w = np.clip(e / 6., 0, 1)
    newC = hc * cov_hair[..., None] + ink * (cov_body - cov_hair)[..., None]
    newC = newC / np.maximum(cov_body, 1e-4)[..., None]
    newC[cov_body < 1e-3] = C[cov_body < 1e-3]
    sub[..., :3] = C * (1 - w[..., None]) + newC * w[..., None]
    sub[..., 3] = (al * (1 - w) + cov_body * w) * 255
    A[y0:y1, x0:x1] = sub

def stroke(A, pts, wmax, col, alpha, taper_top=True):
    H, W = A.shape[:2]; pts = np.array(pts, np.float32)
    t = np.linspace(0, 1, 200)[:, None]
    if len(pts) == 3: P_ = (1 - t) ** 2 * pts[0] + 2 * (1 - t) * t * pts[1] + t ** 2 * pts[2]
    else: P_ = (1 - t) * pts[0] + t * pts[1]
    x0, y0 = np.floor(P_.min(0) - 4).astype(int); x1, y1 = np.ceil(P_.max(0) + 4).astype(int)
    cv_ = np.zeros(((y1 - y0) * U, (x1 - x0) * U), np.float32)
    for k, (x, y) in enumerate(P_):
        f = t[k, 0]; wd = wmax * np.sin(np.pi * min(1, f * 1.15)) ** .6 if taper_top else wmax
        wd = wmax * (np.clip(f / .55, 0, 1) ** .8) * np.clip((1 - f) / .2, 0, 1) ** .5 + 0 * wd
        if wd <= 0.05: continue
        cv2.circle(cv_, (int((x - x0) * U * 16), int((y - y0) * U * 16)), int(wd / 2 * U * 16), 1.0, -1, cv2.LINE_AA, shift=4)
    cov = cv2.resize(cv_, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA) * alpha
    sub = A[y0:y1, x0:x1, :3]; A[y0:y1, x0:x1, :3] = sub * (1 - cov[..., None]) + np.array(col, np.float32) * cov[..., None]

def armpit(A):
    s = A[..., :3].sum(2); H, W = s.shape
    # 1) floating short dark vertical line at lower left: erase top part, taper its new start
    yy, xx = np.mgrid[0:H, 0:W]
    reg = (xx >= 1150) & (xx <= 1166) & (yy >= 1572) & (yy <= 1668)
    dark = reg & (s < 520) & (A[..., 3] > 200)
    fade = np.clip((1652 - yy) / 18., 0, 1)
    src = reg & ~cv2.dilate(dark.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & (s > 520)
    src2 = np.zeros_like(src); src2[1560:1680, 1140:1180] = True; src2 &= (s > 520) & (A[..., 3] > 250) & ~cv2.dilate(dark.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    m = cv2.dilate(dark.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32) * reg * fade
    refill(A, m, src2, 3)
    # 2) smooth the stair-stepped right outline
    armpit_outline(A, 1222, 1462, 1275, 1575, 3.0)
    # 3) strand lines through the blurred fill, following the neighbouring strands
    dk = (214, 128, 146); hl = (240, 170, 182)
    stroke(A, [(1186, 1498), (1190, 1535), (1197.5, 1567)], 1.4, dk, .85)
    stroke(A, [(1204, 1506), (1205, 1545), (1211, 1588)], 1.3, dk, .8)
    stroke(A, [(1221, 1500), (1220, 1535), (1225, 1572)], 1.2, dk, .75)
    stroke(A, [(1195, 1512), (1198, 1545), (1204, 1578)], 1.6, hl, .55)
    return int(m.sum())

def loop_specks(A):
    s = A[..., :3].sum(2); H, W = s.shape
    ink = s < 400
    ref = cv2.medianBlur(np.clip(s / 3, 0, 255).astype(np.uint8), 9).astype(np.float32) * 3
    near = cv2.dilate(ink.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    box = np.zeros((H, W), bool); box[870:1000, 1328:1364] = True
    m = box & near & ~ink & (s > ref + 30) & (A[..., 3] > 200)
    m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & box & ~ink
    src = box & ~m & ~near
    # ink-side neighbours: fill only from hair on the same side via small sigma
    refill(A, m.astype(np.float32), src, 2.5)
    return int(m.sum())

def line_smooth(A, x0, y0, x1, y1, sg=2.0):
    """smooth an ink line lying on opaque fill: ink coverage via projection, SDF-smoothed"""
    sub = A[y0:y1, x0:x1].copy(); C = sub[..., :3]; s = C.sum(2)
    inkm = s < 330; ink = np.median(C[inkm], 0)
    far = cv2.distanceTransform((~inkm).astype(np.uint8), cv2.DIST_L2, 5) > 3
    hm = (far & (s > 520)).astype(np.float32)
    hc = cv2.GaussianBlur(C * hm[..., None], (0, 0), 3) / np.maximum(cv2.GaussianBlur(hm, (0, 0), 3), 1e-4)[..., None]
    hc2 = cv2.GaussianBlur(C * hm[..., None], (0, 0), 8) / np.maximum(cv2.GaussianBlur(hm, (0, 0), 8), 1e-4)[..., None]
    hc = np.where((cv2.GaussianBlur(hm, (0, 0), 3) > .02)[..., None], hc, hc2)
    d = np.clip(((hc - C) * (hc - ink)).sum(2) / np.maximum(((hc - ink) ** 2).sum(2), 1), 0, 1)
    band = cv2.dilate(inkm.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    c = ss(d.astype(np.float32), sg)
    yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0]
    e = np.minimum.reduce([yy, xx, y1 - y0 - 1 - yy, x1 - x0 - 1 - xx]).astype(np.float32)
    w = (np.clip(e / 5., 0, 1) * band)[..., None]
    new = hc * (1 - c[..., None]) + ink * c[..., None]
    sub[..., :3] = C * (1 - w) + new * w
    A[y0:y1, x0:x1] = sub

for nm in ('hair_back', 'hair_back_wave'):
    A = load(nm); print(nm, 'loop specks', loop_specks(A)); line_smooth(A, 1326, 860, 1366, 1000, 2.0); save(nm, A)

A = load('hair_back_wave'); n = dot_split(A); n2 = armpit(A); print('armpit', n2); save('hair_back_wave', A); print('dot', n)

def top_spur(A):
    s = A[..., :3].sum(2); H, W = s.shape
    box = np.zeros((H, W), bool); box[648:688, 770:790] = True
    m = box & (s < 575)
    m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & box
    src = np.zeros((H, W), bool); src[620:710, 740:790] = True; src &= (s > 575) & ~m & (A[..., 3] > 250)
    refill(A, m.astype(np.float32), src, 4)
    col = A[:, 790, :3]; A[654:686, 789:791, :3] = ((col[646:652].mean(0) + col[690:696].mean(0)) / 2)[None]
    return int(m.sum())

A = load('basic_upper_wave'); print('top spur', top_spur(A)); save('basic_upper_wave', A)
