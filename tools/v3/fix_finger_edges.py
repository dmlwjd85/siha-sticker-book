"""Round 10: body_wave_arm_* finger lines - the skin-side edge of the ink lines kept small bumps and a
pale-pink / whitish fringe. Re-derive line coverage from the skin->ink projection, smooth it with a 4x
supersampled SDF and recompose as skin + ink, so the fringe becomes plain skin and the edge is clean.
Outer (transparent-side) edges are untouched (coverage forced to 1 beyond alpha)."""
import sys, glob, os, numpy as np, cv2
from PIL import Image
P = sys.argv[1] if len(sys.argv) > 1 else 'public/v3-demo/parts'
U = 4
def ss(cov, sg):
    up = cv2.resize(cov, (cov.shape[1]*U, cov.shape[0]*U), interpolation=cv2.INTER_LINEAR) > 0.5
    sd = (cv2.distanceTransform(up.astype(np.uint8), cv2.DIST_L2, 5)
          - cv2.distanceTransform((~up).astype(np.uint8), cv2.DIST_L2, 5))
    sd = cv2.GaussianBlur(sd, (0, 0), sg*U)
    return cv2.resize(np.clip(sd/U + 0.5, 0, 1).astype(np.float32), (cov.shape[1], cov.shape[0]), interpolation=cv2.INTER_AREA)
for f in sorted(glob.glob(f'{P}/body_wave_arm_*.png')):
    A = np.array(Image.open(f).convert('RGBA')).astype(np.float32)
    C = A[..., :3]; al = A[..., 3]; op = al >= 250; s = C.sum(2)
    inkm = op & (s < 330)
    ink = np.median(C[inkm], 0)
    # skin reference: blurred colour of skin pixels at least 4px away from ink (fringe excluded)
    far = cv2.distanceTransform((~inkm).astype(np.uint8), cv2.DIST_L2, 5) > 4
    sk = (op & far & (s > 600)).astype(np.float32)
    skin = np.zeros_like(C); den = np.zeros(sk.shape, np.float32); got = np.zeros(sk.shape, bool)
    for sg in (3, 6, 12, 24):
        num = cv2.GaussianBlur(C*sk[..., None], (0, 0), sg); dd = cv2.GaussianBlur(sk, (0, 0), sg)
        ok = ~got & (dd > 0.05); skin[ok] = num[ok]/dd[ok, None]; got |= ok
    d = ink[None, None] - skin
    t = ((C - skin)*d).sum(2) / np.maximum((d*d).sum(2), 1)
    resid = np.linalg.norm(C - skin - t[..., None]*d, axis=2)
    band = cv2.dilate(inkm.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    band &= op & got & (resid < 40)                       # only skin/ink mixtures (not nails, blush etc.)
    cov = np.clip(t, 0, 1).astype(np.float32)
    cov[~op] = 1.0                                         # keep outer contour as is
    cov[op & ~band] = np.where(inkm[op & ~band], 1, 0)
    nc = ss(cov, 3.5)
    # pale fringe: skin-side pixels brighter/pinker than skin with low coverage -> plain skin
    new = skin*(1 - nc[..., None]) + ink[None, None]*nc[..., None]
    ch = band & (np.abs(new - C).max(2) > 2)
    C[ch] = new[ch]
    Image.fromarray(np.clip(A + .5, 0, 255).astype(np.uint8)).save(f)
    print(os.path.basename(f), int(ch.sum()))
