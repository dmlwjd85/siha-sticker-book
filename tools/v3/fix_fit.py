"""의상 상의(basic_upper*) 소매 끝 잔여 조각 정리.
- 팔꿈치 옆 소매 밑단의 닫힌 작은 고리(노란 셔츠 쐐기) 제거
- 소매 바깥 선 왼쪽에 남은 피부색 조각 제거
업스케일 이후(2배 해상도) 좌표 기준. 사용: python3 fix_fit.py PARTS_DIR
"""
import sys, numpy as np
from PIL import Image, ImageDraw
d = sys.argv[1]
LINE = (109, 59, 90)
for n in ['basic_upper', 'basic_upper_wave']:
    p = f'{d}/{n}.png'; a = np.array(Image.open(p).convert('RGBA')).astype(np.int32)
    dark = (a[..., :3].sum(-1) < 330) & (a[..., 3] > 128)
    # 1) 고리 제거: 꼭짓점 아래 영역
    a[527:575, 30:116] = 0
    # 2) 바깥 선 왼쪽 조각
    for y in range(370, 527):
        xs = np.where(dark[y, 0:160])[0]
        if len(xs): a[y, :xs[0]] = 0
    # 2b) 고리 왼쪽 벽 잔여: 소매 바깥 선(75,470)->(100,522) 왼쪽
    for y in range(470, 527):
        xl = int(75 + (y - 470) * 25 / 52) - 4
        a[y, :max(xl, 0)] = 0
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    # 3) 꼭짓점 둥근 마감
    g = ImageDraw.Draw(im); g.ellipse((99, 519, 109, 529), fill=LINE + (255,))
    im.save(p)
    print('fixed', n)
