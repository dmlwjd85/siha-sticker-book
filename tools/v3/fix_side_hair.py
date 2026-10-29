"""Round 8: side hair cleanup (run from backups /workspace/qa8/{bu,hb}_r7.png; not idempotent).
1) body_upper: the face/ear outline under hair_front's soft edge showed through as a faint grey
   sketch line. Remove dark body_upper pixels inside hair_front's footprint (+4px) where hair_back
   is opaque beneath.
2) hair_back: smooth the square grey-pink patch at the tie loop, thin the loop outline."""
import sys, numpy as np, cv2
from PIL import Image
from scipy import ndimage
P = sys.argv[1]
def load(n): return np.array(Image.open(f'{P}/{n}.png').convert('RGBA')).astype(np.float32)
def save(n, a): Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(f'{P}/{n}.png')
def place(src, dx, dy, shape):
    out = np.zeros(shape, np.float32); H, W = src.shape
    y0, x0 = max(0, dy), max(0, dx); y1, x1 = min(shape[0], H + dy), min(shape[1], W + dx)
    out[y0:y1, x0:x1] = src[y0 - dy:y1 - dy, x0 - dx:x1 - dx]; return out

U = load('body_upper'); F = load('hair_front'); B = load('hair_back')
fa = place(F[..., 3], 188, -6, U.shape[:2])          # hf pixel = bu - (188,-6)
ba = place(B[..., 3], -172, -38, U.shape[:2])        # hb pixel = bu + (172,38)
foot = cv2.dilate((fa > 0).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
inner = cv2.erode((fa > 250).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
foot &= ~inner
dark = U[..., :3].sum(-1) < 520
m = foot & (ba > 250) & dark & (U[..., 3] > 0) & (np.mgrid[:U.shape[0], :U.shape[1]][0] < 1000)
U[..., 3][m] = 0
print('body_upper outline under hair_front', int(m.sum()))
save('body_upper', U)

# 1b) hair_front soft edge over hair_back: blend edge band toward the hair_back colour beneath so
#     jagged dark ticks/grey fringe at the side-lock boundary disappear.
hbF = np.zeros(F.shape, np.float32)                   # hb resampled into hf coords: hb = hf + (360,32)
H, W = F.shape[:2]; hbF[:] = B[32:32 + H, 360:360 + W] if B.shape[0] >= 32 + H else 0
d = ndimage.distance_transform_edt(F[..., 3] > 128)
yy, xx = np.mgrid[:H, :W]
side = ((xx < 330) | (xx > W - 330)) & (yy > 240) & (yy < 940)
c0 = F[..., :3]; skin = (c0[..., 1] > 195) & (c0[..., 0] - c0[..., 1] < 40)
skin = (cv2.dilate(skin.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & (xx > 150) & (xx < W - 150)
w = np.clip((90 - d) / 10, 0, 1) * side * ~skin * (hbF[..., 3] > 250) * (F[..., 3] > 0)
w = cv2.GaussianBlur(w.astype(np.float32), (0, 0), 1.2) * (F[..., 3] > 0)
F[..., :3] = F[..., :3] * (1 - w[..., None]) + hbF[..., :3] * w[..., None]
print('hair_front edge blend', int((w > 0.05).sum()))
save('hair_front', F)

# 1c) hair_back: broken line fragments / light slivers along strand lines where hair_front's top
#     edge ends (left & right side locks). Keep the main line, refill the rest with hair colour.
def frag_clean(A, x0, x1, y0, y1):
    r = A[y0:y1, x0:x1]; s = r[..., :3].sum(-1)
    dark = s < 450
    lb, n = ndimage.label(dark)
    if n:
        big = np.argmax(ndimage.sum(dark, lb, range(1, n + 1))) + 1
        keep = cv2.dilate((lb == big).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    else: keep = np.zeros_like(dark)
    med = np.median(s[~dark])
    odd = ~keep & ((np.abs(s - med) > 28) | dark) & (r[..., 3] > 0)
    good = ~odd & ~keep
    _, (iy, ix) = ndimage.distance_transform_edt(~good, return_indices=True)
    fill = r[..., :3].copy(); fill[odd] = r[..., :3][iy[odd], ix[odd]]
    fill = cv2.GaussianBlur(fill, (0, 0), 1.5)
    w = cv2.GaussianBlur(odd.astype(np.float32), (0, 0), 1.0); w = np.maximum(w, odd)
    r[..., :3] = r[..., :3] * (1 - w[..., None]) + fill * w[..., None]
    return int(odd.sum())
for name in ['hair_back', 'hair_back_wave']:
    A = load(name)
    n = frag_clean(A, 386, 418, 380, 450) + frag_clean(A, 1232, 1268, 388, 506)
    print(name, 'fragments', n); save(name, A)

# 2) tie loops: pull the loop outline in by ~1px per side (body outline weight) and fill pinholes;
#    lift the square grey-pink patches around the knot to the surrounding hair tone (gain, feathered).
LOOPS = [  # box, seed inside ring, knot box, patch seed points (hair_back px)
    ((175, 795, 340, 1115), (250, 1000), (262, 812, 336, 872), [(280, 822), (318, 840)]),
    ((1315, 795, 1465, 1115), (1405, 1000), (1330, 822, 1372, 866), [(1330, 820), (1327, 865), (1342, 930), (1380, 845)], (1362, 828, 1388, 880)),
]
def loop_fix(A, box, seed, knot, pseeds, extra=None):
    x0, y0, x1, y1 = box; r = A[y0:y1, x0:x1]; c = r[..., :3]; s = c.sum(-1)
    dark = (s < 420) & (r[..., 3] > 200)
    # alpha pinholes inside the outline
    ah = (r[..., 3] < 250) & ndimage.binary_fill_holes(r[..., 3] >= 250)
    r[..., 3][ah] = 255
    c[ah] = np.median(c[dark], axis=0); s = c.sum(-1); dark = (s < 420) & (r[..., 3] > 200)
    darkc = ndimage.binary_closing(dark, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)).astype(bool))
    lb, _ = ndimage.label(~darkc); interior = lb == lb[seed[1] - y0, seed[0] - x0]
    interior = cv2.dilate(interior.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~dark
    di = ndimage.distance_transform_edt(~interior)
    kn = np.zeros_like(dark); kn[knot[1] - y0:knot[3] - y0, knot[0] - x0:knot[2] - x0] = True
    # pinholes inside the outline (also ones open on a diagonal)
    holes = ndimage.binary_fill_holes(ndimage.binary_closing(dark, np.ones((3, 3)))) & ~dark
    lh, nh = ndimage.label(holes)
    small = np.isin(lh, [i for i in range(1, nh + 1) if (lh == i).sum() <= 16])
    col = np.median(c[dark & (ndimage.distance_transform_edt(dark) >= 2)], axis=0)
    df = cv2.blur(dark.astype(np.float32), (5, 5))
    small |= ~dark & (df > 0.55) & (s > 450) & cv2.dilate(dark.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ((di <= 14) | kn)
    c[small] = col; dark |= small
    dt = ndimage.distance_transform_edt(dark)
    thickz = cv2.dilate((dt >= 3.5).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    zone = cv2.dilate((dark & ((di <= 12) | kn) & thickz).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    zone = cv2.GaussianBlur(zone.astype(np.float32), (0, 0), 1.5)
    # soft coverage of the existing outline from colour (0 = hair, 1 = outline)
    good = (s > 560) & (r[..., 3] > 200)
    _, (iy, ix) = ndimage.distance_transform_edt(~good, return_indices=True)
    bgc = cv2.GaussianBlur(c[iy, ix], (0, 0), 1.0)
    num = ((bgc - c) * (bgc - col)).sum(-1); den = ((bgc - col) ** 2).sum(-1) + 1e-3
    cov = np.clip(num / den, 0, 1)
    # signed distance of the 0.5 iso-line, smoothed, pulled in by 1.1px
    inside = cov > 0.5
    sd = ndimage.distance_transform_edt(inside) - ndimage.distance_transform_edt(~inside)
    sd = cv2.GaussianBlur(sd.astype(np.float32), (0, 0), 1.1)
    ncov = np.clip(sd - 1.1 + 0.5, 0, 1)
    ncov = cov * (1 - zone) + np.minimum(ncov, cov + 0.0) * zone
    ncov = np.where(zone > 0, np.minimum(ncov, 1), cov)
    c[:] = np.where((zone > 0)[..., None], bgc * (1 - ncov[..., None]) + col * ncov[..., None], c)
    rem = (zone > 0) & (cov - ncov > 0.3)
    # patches: flat cel-fill colour (from the old loop-hole fill) that spilled outside the ring as
    # rectangles -> refill from the surrounding hair (normalized convolution, excludes outline)
    flatc = np.array([241.5, 174.5, 184.5])
    flat = (np.abs(c - flatc).max(-1) <= 6) & ~interior
    if extra is not None:  # flat fill leaking up an open channel: fade it into the light hair above (no hard edge)
        ex0, ey0, ex1, ey1 = extra
        sub = c[ey0 - y0:ey1 - y0, ex0 - x0:ex1 - x0]
        fm = (np.abs(sub - flatc).max(-1) <= 10) | ((sub.sum(-1) > 560) & (sub.sum(-1) < 650))
        light = np.array([254.0, 197.0, 204.0])
        t = np.clip((np.arange(sub.shape[0]) / (sub.shape[0] - 1)), 0, 1); t = t * t * (3 - 2 * t)
        w = (1 - t)[:, None, None] * fm[..., None]
        w = cv2.GaussianBlur(w[..., 0].astype(np.float32), (0, 0), 1.5)[..., None] * (sub.sum(-1) > 450)[..., None]
        sub[:] = sub * (1 - w) + light * w
        interior[ey0 - y0:ey1 - y0, ex0 - x0:ex1 - x0] = True  # don't refill it again below
    lbf, nf = ndimage.label(flat)
    flat = np.isin(lbf, [i for i in range(1, nf + 1) if (lbf == i).sum() >= 12])
    out = cv2.dilate(flat.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & ~interior & (ncov < 0.35) & ~dark
    sur = ~out & ~interior & (ncov < 0.05) & ~dark & (r[..., 3] > 200) & ~cv2.dilate(out.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    acc = np.zeros_like(c); wsum = np.zeros(c.shape[:2], np.float32); todo = out.copy(); filled = c.copy()
    for sg in (3, 6, 12, 24):
        num = cv2.GaussianBlur(c * sur[..., None], (0, 0), sg); den = cv2.GaussianBlur(sur.astype(np.float32), (0, 0), sg)
        ok = todo & (den > 0.08)
        filled[ok] = num[ok] / den[ok][..., None]; todo &= ~ok
    # keep the outline anti-aliasing: blend by (1-ncov)
    wgt = (1 - ncov)[..., None] * out[..., None]
    base = filled * (1 - ncov[..., None]) + col * ncov[..., None]
    c[:] = np.where(out[..., None], base, c)
    # erase faint 1px seam lines left at old patch borders: median-smooth the open hair zone away from outlines
    far = (ndimage.distance_transform_edt(~dark) > 3) & ~interior & (r[..., 3] > 250)
    far &= ~(ndimage.distance_transform_edt(~interior) <= 3)
    med = cv2.medianBlur(np.clip(c, 0, 255).astype(np.uint8), 7).astype(c.dtype)
    dev = np.abs(c - med).max(-1) > 3
    keep = (c[..., 1] < 150) | (med[..., 1] < 150)
    c[far & dev & ~keep] = med[far & dev & ~keep]
    return int(rem.sum()), int(small.sum()), int(flat.sum())
for name in ['hair_back', 'hair_back_wave']:
    A = load(name)
    for L in LOOPS: print(name, 'loop', loop_fix(A, *L))
    save(name, A)
