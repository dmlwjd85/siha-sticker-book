"""흔드는 팔(body_wave_arm_0..8) 아래팔 바깥 윤곽 정리.
휘어 만든 프레임이라 윤곽선이 울퉁불퉁하고(계단·혹), 선 바깥에 옅은 회색/크림 띠가 남는다.
실루엣 외곽선을 따라 부드럽게 다듬고(손목 아래만, 손가락은 그대로), 바깥 띠를 지우고,
일정한 굵기의 선으로 다시 그린다. 업스케일(2배) 이후 좌표 기준. 사용: python3 fix_wave_arm.py PARTS_DIR
"""
import sys, numpy as np, cv2
from PIL import Image
from scipy.ndimage import gaussian_filter1d
d = sys.argv[1]
LINE = np.array([109, 59, 90]); SS = 4; LW = 8.5   # 선 굵기(2배 해상도 px)
for i in range(9):
    p = f'{d}/body_wave_arm_{i}.png'
    a = np.array(Image.open(p).convert('RGBA')).astype(np.float32)
    H, W = a.shape[:2]
    M = (a[..., 3] > 128).astype(np.uint8)
    cs, _ = cv2.findContours(M, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)[:, 0, :].astype(np.float64)
    wrist = 0.42 * H
    # 대상: 아래팔 바깥(오른쪽) 윤곽만. 양 끝은 서서히 원래 선으로 이어지게
    rowmax = np.full(H, -1.0)
    for (x, y) in c: rowmax[int(y)] = max(rowmax[int(y)], x)
    rm = rowmax[c[:, 1].astype(int)]
    sel = (c[:, 0] >= rm - 3) & (c[:, 1] > wrist) & (c[:, 1] < H - 30)
    # 아래팔 안쪽(왼쪽) 윤곽: 다듬지 않고 선 굵기만 고르게(가늘게 끊긴 회색 선 보강)
    lsel = (c[:, 0] < rm - 40) & (c[:, 0] > rm - 175) & (c[:, 1] > wrist) & (c[:, 1] < H - 30)
    wgt = gaussian_filter1d(sel.astype(np.float64), 12, mode='wrap')
    wgt = np.clip((wgt - 0.1) / 0.8, 0, 1)[:, None]
    sm = np.stack([gaussian_filter1d(c[:, k], 9, mode='wrap') for k in range(2)], 1)
    sm = c * (1 - wgt) + sm * wgt
    # 새 실루엣(슈퍼샘플 안티앨리어싱)
    big = np.zeros((H * SS, W * SS), np.uint8)
    cv2.fillPoly(big, [np.round(sm * SS + SS / 2).astype(np.int32)], 255, cv2.LINE_AA)
    newA = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    # 경계에서 이미지 테두리(어깨 쪽 잘린 면)는 원래 알파 유지
    border = np.zeros((H, W), bool); border[:, :6] = True; border[:, -3:] = True; border[-6:, :] = True; border[:6, :] = True
    oldA = a[..., 3] / 255
    inside = (cv2.erode(M, np.ones((5, 5), np.uint8)) > 0)
    rgb = a[..., :3]
    light = inside & (rgb.sum(-1) > 650)
    skin = np.median(rgb[light], 0)
    # 경계 근처(선 지대)는 일단 피부색으로 지운 뒤 선을 새로 긋는다
    dist = cv2.distanceTransform((newA > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    zm = np.zeros((H, W), np.uint8)
    for k in np.where(wgt[:, 0] > 0.5)[0]:
        cv2.circle(zm, (int(sm[k, 0]), int(sm[k, 1])), 14, 1, -1)
    zone = (dist < 16) & (zm > 0)
    darkish = rgb.sum(-1) < 640
    rgb[zone & darkish & ~border] = skin
    rgb[(newA > 0) & (oldA < 0.6) & ~border & (zm > 0)] = skin
    # 선: 매끈한 윤곽을 굵게 그리고 실루엣 안쪽만 남김. 테두리에 붙은 점은 선 없음
    lb = np.zeros((H * SS, W * SS), np.uint8)
    keep = wgt[:, 0] > 0.02
    seg = []
    for k in range(len(sm)):
        if keep[k]: seg.append(sm[k])
        elif seg:
            if len(seg) > 2: cv2.polylines(lb, [np.round(np.array(seg) * SS + SS / 2).astype(np.int32)], False, 255, int(LW * 2 * SS), cv2.LINE_AA)
            seg = []
    if len(seg) > 2: cv2.polylines(lb, [np.round(np.array(seg) * SS + SS / 2).astype(np.int32)], keep[0], 255, int(LW * 2 * SS), cv2.LINE_AA)
    # 왼쪽 윤곽 보강선(원래 경계 그대로, 같은 굵기)
    seg = []
    for k in range(len(c)):
        if lsel[k]: seg.append(c[k])
        elif seg:
            if len(seg) > 2: cv2.polylines(lb, [np.round(np.array(seg) * SS + SS / 2).astype(np.int32)], False, 255, int(LW * 2 * SS), cv2.LINE_AA)
            seg = []
    if len(seg) > 2: cv2.polylines(lb, [np.round(np.array(seg) * SS + SS / 2).astype(np.int32)], False, 255, int(LW * 2 * SS), cv2.LINE_AA)
    la = cv2.resize(lb, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255
    rgb[:] = rgb * (1 - la) + LINE * la
    A = np.where(border | (zm == 0), oldA, newA)
    a[..., :3] = rgb; a[..., 3] = A * 255
    Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(p); print('fixed', i)
