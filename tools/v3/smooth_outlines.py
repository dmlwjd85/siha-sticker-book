"""업스케일 직후 공정: 모든 부품의 바깥 외곽선을 매끈한 한 줄로 다시 그린다.
(touchup → clean_edges → patch_regen → fix_elbow → upscale_parts → smooth_outlines → fix_fit → fill_hair_holes → fix_wave_arm → fill_head_gaps)
1) 알파 실루엣의 윤곽점을 호 길이 방향 가우시안(스플라인과 같은 저역 통과)으로 매끈하게, 머리끝처럼 뾰족한 곳(편차 큼)은 원래 점 유지
2) 4배 슈퍼샘플로 새 실루엣을 그려 안티앨리어싱 알파를 만들고, 실루엣 밖 번짐(반투명 색)은 모두 지움
3) 원래 외곽선이 있던 곳만 같은 굵기(몸 외곽선 기준)로 선을 다시 칠하고, 떨리던 옛 선 안쪽 찌꺼기는 주변 색으로 메움
사용: python3 smooth_outlines.py PARTS_DIR [부품이름...]"""
import sys, os, glob, numpy as np, cv2
from PIL import Image
from scipy.ndimage import gaussian_filter1d
SKIP = {'eyes_closed', 'acc_ribbon', 'acc_star', 'prop_mic'}  # 소품은 선이 없는 색면 위주라 제외
LW_BODY = None
def old_lw(a, A):
    dk = (a[..., :3].astype(int).sum(-1) < 330) & A
    dt = cv2.distanceTransform(A.astype(np.uint8), cv2.DIST_L2, 5)
    for k in range(1, 30):
        band = (dt > k - 1) & (dt <= k)
        if band.sum() == 0 or dk[band].mean() < 0.5: return max(k - 1, 2)
    return 4
def smooth_contour(c, S):
    p = c[:, 0, :].astype(float)
    if len(p) < 40: return p
    ps = np.stack([gaussian_filter1d(p[:, i], S, mode='wrap') for i in range(2)], 1)
    dev = np.linalg.norm(p - ps, axis=1)
    w = np.clip(1 - (dev - 3.5) / 3.0, 0, 1)  # 뾰족한 끝(편차 큼)은 원래 점
    w = gaussian_filter1d(w, 3, mode='wrap')
    return ps * w[:, None] + p * (1 - w[:, None])
def run(p, lw_target, S=8):
    a = np.array(Image.open(p).convert('RGBA')); H, W = a.shape[:2]
    A = a[..., 3] > 128
    lwo = old_lw(a, A)
    if lwo < 6: lw_target = lwo  # 가는 선 부품(앞머리 등)은 원래 굵기 유지 — 굵히면 점처럼 뭉침
    cs, hi = cv2.findContours(A.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    Z = 4; big = np.zeros((H * Z, W * Z), np.uint8)
    for i, c in enumerate(cs):
        if len(c) < 12 and hi[0][i][3] < 0: continue
        q = (smooth_contour(c, S) * Z + Z / 2).astype(np.int32)
        cv2.fillPoly(big, [q], 0 if hi[0][i][3] >= 0 else 255)
    cov = cv2.resize(big.astype(np.float32) / 255, (W, H), interpolation=cv2.INTER_AREA)
    An = cov > 0.5
    dk = (a[..., :3].astype(int).sum(-1) < 330) & A
    LINE = np.median(a[dk][:, :3], 0) if dk.sum() else np.array([109, 59, 90])
    dto = cv2.distanceTransform(A.astype(np.uint8), cv2.DIST_L2, 5)
    dtn = cv2.distanceTransform(An.astype(np.uint8), cv2.DIST_L2, 5)
    # 옛 외곽선이 있던 자리(가장자리 근처 어두운 띠) → 새 선을 칠할 자리
    oldline = dk & (dto <= lwo + 1.5)
    had = cv2.dilate(oldline.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0  # 선 없던 잘린 이음부에는 선을 새로 만들지 않음
    out = a.astype(np.float32).copy()
    # 옛 선 찌꺼기(새 선 굵기 밖) 메우기
    junk = (oldline & (dtn >= lw_target)) | (An & ~A & (dtn >= lw_target))
    if junk.any():
        src = a[..., :3].copy(); src[junk] = 0
        fill = cv2.inpaint(src, junk.astype(np.uint8), 4, cv2.INPAINT_TELEA)
        out[junk, :3] = fill[junk]
    band = An & (dtn < lw_target) & had
    soft = np.clip(lw_target + 0.5 - dtn, 0, 1)
    edge = (cov > 0) & (cov < 1) & had
    for ch in range(3):
        out[..., ch] = np.where(band, out[..., ch] * (1 - soft) + LINE[ch] * soft, out[..., ch])
        out[..., ch] = np.where(edge & ~An, LINE[ch], out[..., ch])
    alpha = np.where(had | ~A, cov * 255, a[..., 3])  # 선 있던 곳은 새 실루엣 알파, 이음부(선 없음)는 원래 알파
    alpha = np.where(cov <= 0, 0, alpha)
    out[..., 3] = np.minimum(alpha, 255)
    Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(p)
    return lwo
if __name__ == '__main__':
    d = sys.argv[1]
    names = sys.argv[2:] or [os.path.basename(f)[:-4] for f in sorted(glob.glob(f'{d}/*.png'))]
    b = np.array(Image.open(f'{d}/body_lower.png').convert('RGBA'))
    LW = old_lw(b, b[..., 3] > 128)  # 몸 외곽선 굵기 기준
    for n in names:
        if n in SKIP: continue
        S = 20 if n.startswith(('body_lower', 'basic_lower')) else 8   # 다리는 더 길게 매끈
        lo = run(f'{d}/{n}.png', LW, S); print(n, 'old lw', lo, '→', LW if lo >= 6 else lo)
