"""흰 속옷(맨몸 옷차림) 안쪽의 분홍 번짐(머리색이 비친 듯한 업스케일 얼룩)을 흰색으로 정리한다.
대상: body_upper*의 skel y>1060(허리 근처) 영역, 순백(min>248) 가까이(6px)에 있는 연분홍(b>=g) 픽셀. 피부(b<g)·머리(g<190)는 제외.
사용: python3 clean_white_tint.py PARTS_DIR"""
import sys, numpy as np, cv2
from PIL import Image
d = sys.argv[1]
for n, (ox, oy) in {'body_upper': (389, 121), 'body_upper_wave': (389, 121)}.items():
    p = f'{d}/{n}.png'; a = np.array(Image.open(p).convert('RGBA')); c = a[..., :3].astype(int)
    white = (c.min(-1) > 248) & (a[..., 3] > 250)
    near = cv2.dilate(white.astype(np.uint8), np.ones((13, 13), np.uint8)) > 0
    tint = (c[..., 0] > 235) & (c[..., 1] > 190) & (c[..., 2] >= c[..., 1]) & (c.min(-1) <= 248) & (a[..., 3] > 0)
    rows = (np.arange(a.shape[0]) / 2 + oy > 1060)[:, None]  # 허리 근처만 (가슴 쪽까지 하면 흰 바탕에 얼룩 경계가 생김)
    m = tint & near & rows
    for _ in range(3):  # 번짐 덩어리 안쪽까지
        near = cv2.dilate((white | m).astype(np.uint8), np.ones((13, 13), np.uint8)) > 0; m = tint & near & rows
    w = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 3) * tint  # 경계를 부드럽게
    w = np.maximum(w, m.astype(np.float32))
    a[..., :3] = np.clip(c + (254 - c) * w[..., None], 0, 255).astype(np.uint8)
    Image.fromarray(a).save(p); print(n, int(m.sum()))
