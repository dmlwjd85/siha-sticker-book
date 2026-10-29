"""Round 9: none-outfit armpit area of hair_back_wave - erase the red diagonal seam line and the dark
marks (blob with holes) next to the outline, refill from surrounding hair and soften the tone seam."""
import sys, numpy as np, cv2
from PIL import Image
P = sys.argv[1] if len(sys.argv) > 1 else 'public/v3-demo/parts'
# hair_back_wave only (hair_back has a different drawing here; the wave changeBox covers this area)
for name in ['hair_back_wave']:
    f = f'{P}/{name}.png'
    A = np.array(Image.open(f).convert('RGBA')).astype(np.float32)
    s = A[..., :3].sum(2); op = A[..., 3] > 250
    H, W = s.shape
    m = np.zeros((H, W), bool)
    # diagonal seam: corridor around polyline
    poly = np.array([(1150, 1580), (1212, 1508), (1229, 1458)], np.int32)
    cor = np.zeros((H, W), np.uint8); cv2.polylines(cor, [poly], False, 1, 9)
    m |= (cor > 0) & (s < 560) & op
    # dark blob + holes near the outline (keep the outline itself: x <= 1241)
    bb = np.zeros((H, W), bool); bb[1460:1545, 1218:1240] = True  # outline starts at x>=1240 here
    m |= bb & ((s < 600) | (A[..., 3] < 250))  # blob ink + its transparent holes
    # the light holes inside the blob
    holes = bb & op & (s >= 600)
    blobd = cv2.dilate((bb & (s < 600)).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    m |= holes & blobd
    m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    m &= op | bb
    A[..., 3][m] = 255; op = A[..., 3] > 250
    keep = op & ~m & (s > 450)  # never sample the outline ink
    C = A[..., :3].copy()
    out = C.copy(); filled = np.zeros((H, W), bool)
    for sg in (2, 4, 8, 16):
        k = keep.astype(np.float32)
        num = cv2.GaussianBlur(C * k[..., None], (0, 0), sg); den = cv2.GaussianBlur(k, (0, 0), sg)
        ok = m & ~filled & (den > 0.05)
        out[ok] = num[ok] / den[ok, None]; filled |= ok
    # soften the tone seam the line separated
    seam = cv2.dilate((cor > 0).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    seam = cv2.GaussianBlur(seam, (0, 0), 3) * (op & (s > 450))
    k = (op & (s > 450)).astype(np.float32)
    bl = cv2.GaussianBlur(out * k[..., None], (0, 0), 4) / np.maximum(cv2.GaussianBlur(k, (0, 0), 4), 1e-3)[..., None]
    out = out * (1 - seam[..., None]) + bl * seam[..., None]
    A[..., :3] = np.where(op[..., None], out, A[..., :3])
    Image.fromarray(np.clip(A + .5, 0, 255).astype(np.uint8)).save(f)
    print(name, 'armpit fixed px', int(m.sum()))
