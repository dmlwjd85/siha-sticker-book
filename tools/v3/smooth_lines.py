"""Round 9: smooth every line in every part.
- outer contour: alpha coverage -> 4x supersampled signed distance -> Gaussian -> area downsample.
- interior ink lines (>=4px from transparency): ink coverage from colour, same supersampled smoothing.
Removes jitter, stair-steps and pinhole breaks; tight curvature at line ends tapers naturally.
Eye interiors (large dark fills, highlight holes) and thin strands are protected so the face does not change.
Usage: smooth_lines.py PARTS_DIR [names...]"""
import sys, glob, os, numpy as np, cv2
from PIL import Image
from scipy import ndimage
P = sys.argv[1]
names = sys.argv[2:] or sorted(os.path.basename(f)[:-4] for f in glob.glob(f'{P}/*.png'))
SG = {'body_upper': 1.4, 'eyes_closed': 0.8, 'hair_front': 1.4}
U = 4
EYES = {'body_upper': [(320, 480, 820, 790)], 'eyes_closed': [(0, 0, 9999, 9999)],
        'hair_front': [(850, 280, 910, 460)]}  # graded-tone strand: ink pass would split its gradient
def ss_smooth(cov, sg, sel):
    """return smoothed coverage; only tiles containing sel are processed"""
    out = cov.copy(); H, W = cov.shape; T = 192; M = 12
    ys, xs = np.nonzero(sel)
    if len(ys) == 0: return out
    for ty in range(ys.min() // T * T, ys.max() + 1, T):
        for tx in range(xs.min() // T * T, xs.max() + 1, T):
            if not sel[ty:ty + T, tx:tx + T].any(): continue
            y0, x0 = max(0, ty - M), max(0, tx - M); y1, x1 = min(H, ty + T + M), min(W, tx + T + M)
            c = cov[y0:y1, x0:x1]
            up = cv2.resize(c, ((x1 - x0) * U, (y1 - y0) * U), interpolation=cv2.INTER_LINEAR)
            ins = up > 0.5
            if ins.all() or not ins.any(): continue
            sd = (cv2.distanceTransform(ins.astype(np.uint8), cv2.DIST_L2, 5)
                  - cv2.distanceTransform((~ins).astype(np.uint8), cv2.DIST_L2, 5))
            sd = cv2.GaussianBlur(sd, (0, 0), sg * U)
            hi = np.clip(sd + 0.5, 0, 1).astype(np.float32)
            dn = cv2.resize(hi, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
            sy, sx = ty - y0, tx - x0
            hh, ww = min(T, H - ty), min(T, W - tx)
            out[ty:ty + hh, tx:tx + ww] = dn[sy:sy + hh, sx:sx + ww]
    return out
def run(name):
    p = f'{P}/{name}.png'; A = np.array(Image.open(p).convert('RGBA')).astype(np.float32)
    sg = SG.get(name, 2.0)
    a = A[..., 3] / 255.0
    # 1) outer contour
    edge = (a > 0.02) & (a < 0.98)
    edge = cv2.dilate(edge.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    na = ss_smooth(a.astype(np.float32), sg, edge)
    # small transparent holes stay as they are
    hol = ndimage.binary_fill_holes(a > 0.5) & ~(a > 0.5)
    na = np.where(cv2.dilate(hol.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool), a, na)
    na = np.where(edge, na, a)
    A[..., 3] = na * 255
    # 2) interior ink lines
    c = A[..., :3]; s = c.sum(-1); op = A[..., 3] > 250
    deep = op
    core = deep & (s < 320)
    if core.sum() < 50:
        Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)).save(p); return 0
    ink = np.median(c[core], axis=0)
    light = op & (s > ink.sum() + 240)
    _, (iy, ix) = ndimage.distance_transform_edt(~light, return_indices=True)
    bgc = cv2.GaussianBlur(c[iy, ix], (0, 0), 1.0)
    d = bgc - ink; dd = (d * d).sum(-1) + 1e-3
    t = np.clip(((bgc - c) * d).sum(-1) / dd, 0, 1)
    resid = np.sqrt(((c - (bgc - t[..., None] * d)) ** 2).sum(-1))
    onseg = (resid < 22) & deep & (dd > 170 ** 2)
    cov = np.where(onseg, t, 0.0).astype(np.float32)
    cov[A[..., 3] < 250] = 1.0   # beyond the alpha edge counts as ink, so outer outlines have no fake edge
    onseg = onseg | (A[..., 3] < 250)
    inside = cov > 0.5
    dt = ndimage.distance_transform_edt(inside)
    li, ni = ndimage.label(inside)
    if ni == 0:
        Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)).save(p); return 0
    mx = ndimage.maximum(dt, li, range(1, ni + 1))
    dto = ndimage.distance_transform_edt(inside & op)
    lio, nio = ndimage.label(inside & op)
    mxo = ndimage.maximum(dto, lio, range(1, nio + 1)) if nio else np.array([])
    fat = cv2.dilate((dto > 5.5).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & inside  # interior of dark masses: leave
    thin = np.isin(lio, 1 + np.nonzero(mxo < 1.5)[0])     # hairline strands: leave
    holes = ndimage.binary_fill_holes(inside) & ~inside
    lh, nh = ndimage.label(holes)
    hs = ndimage.sum(holes, lh, range(1, nh + 1)) if nh else []
    holes = np.isin(lh, 1 + np.nonzero(np.array(hs) < 400)[0]) if nh else holes  # small highlight holes only
    rim = cv2.dilate((~deep).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    touch = np.isin(li, np.unique(li[rim & inside]))       # outer outline: handled by alpha
    for (bx0, by0, bx1, by1) in EYES.get(name, []):
        holes[by0:by1, bx0:bx1] = True
    mt = ndimage.maximum(np.where(A[..., 3] < 250, 0, t), lio, range(1, nio + 1)) if nio else np.array([])
    weak = np.isin(lio, 1 + np.nonzero(mt < 0.85)[0])     # light stripes / tinted lines: not ink
    bad = deep & op & ~onseg & (s < ink.sum() + 240)      # unmodelled colours (red fills etc.) nearby
    bad = cv2.dilate(bad.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    holes = holes | weak | bad
    prot = cv2.dilate((fat | thin | holes).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) | ~op
    sel = cv2.dilate((inside & ~prot).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~prot
    ncov = ss_smooth(cov, sg, sel)
    ch = sel & (np.abs(ncov - cov) > 0.02) & (onseg | (ncov > 0.02))
    newc = bgc - ncov[..., None] * d
    ch &= A[..., 3] >= 250
    c[ch] = newc[ch]
    Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)).save(p)
    return int(ch.sum())
for n in names:
    print(n, run(n), flush=True)
