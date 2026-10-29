"""흔들기 팔 0번 프레임: 오른쪽 바깥선이 이미지 경계에 잘려 생긴 평평한 꺾임을 부드러운 곡선으로 다시 그린다.
사용: python3 fix_wave_arm0_edge.py PARTS_DIR"""
import sys, numpy as np
from PIL import Image
p = f'{sys.argv[1]}/body_wave_arm_0.png'
a = np.array(Image.open(p).convert('RGBA')).astype(float); H, W = a.shape[:2]
LINE = np.array([109, 59, 90.]); 
ys = list(range(600, 770)) + list(range(850, 960))
ex = [np.where(a[y, :, 3] > 128)[0].max() for y in ys]
c = np.polyfit(ys, ex, 3)
skin = np.median(a[800, 330:360, :3], 0)
yy = np.arange(640, 960); tr = np.polyval(c, yy); yc = yy[tr.argmax()]
A = max(0, tr.max() - (W - 6))
for y in range(650, 950):
    e = np.polyval(c, y) - A * np.exp(-((y - yc) / 90.0) ** 2)
    w = min(1, (y - 650) / 50, (950 - y) / 50)  # 양 끝은 원래 윤곽선으로 부드럽게 이어 붙임
    e = w * e + (1 - w) * (np.where(a[y, :, 3] > 128)[0].max() + 0.5)
    for x in range(int(e) - 26, W):
        d = e - (x + 0.5)  # 바깥선까지 거리
        if d < -0.5: a[y, x, 3] = 0; continue
        cov = min(1, d + 0.5)
        if d < 8.5: col = LINE
        elif d < 9.5: col = LINE * (9.5 - d) + skin * (d - 8.5)
        else:
            if (a[y, x, :3].sum() < 450): col = skin
            else: continue
        a[y, x, :3] = col; a[y, x, 3] = 255 * cov
Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(p); print('ok', c)
