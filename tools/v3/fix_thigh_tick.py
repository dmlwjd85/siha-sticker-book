"""맨몸 하의(body_lower*) 왼쪽 허벅지 안쪽 선의 작은 가시 2개(업스케일 잔재)를 지운다.
행 436~478, x 400~470(2배 파츠 좌표)에서 안쪽 선의 오른쪽 10px만 남기고 왼쪽으로 튀어나온 어두운 픽셀을 바로 옆 피부색으로 칠한다."""
import sys, numpy as np
from PIL import Image
d = sys.argv[1]
for n in ('body_lower', 'body_lower_wave'):
    p = f'{d}/{n}.png'; a = np.array(Image.open(p).convert('RGBA')); c = a[..., :3].astype(int); k = 0
    for y in range(434, 480):
        dk = np.where((a[y, 400:470, 3] > 128) & (c[y, 400:470].sum(-1) < 400))[0]
        if len(dk) == 0: continue
        r = dk.max(); l = dk.min()
        # 연결된 오른쪽 덩어리만
        if r - l + 1 > 11:
            src = a[y, 400 + l - 3].copy()
            for x in range(l, r - 9): 
                a[y, 400 + x] = src; k += 1
            # 경계 반투명/중간색 정리: 선 왼쪽 1px 은 피부와 선의 중간
    Image.fromarray(a).save(p); print(n, k)
