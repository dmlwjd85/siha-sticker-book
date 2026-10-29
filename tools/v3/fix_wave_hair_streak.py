"""흔들기용 뒷머리(hair_back_wave): 기본 뒷머리에는 몸통 자리 구멍과 그 테두리 선이 있다.
흔들기 때 팔이 비켜 간 자리를 머리로 메우면서 옛 테두리 선이 옅은 줄(흰·회색 자국)로 남았다.
옛 테두리 자리(기본 파츠의 구멍 옆 어두운 선, 넓힘)에 있는 흔들기 파츠 픽셀 중 지금 선(어두움)이 아닌 것을
가장 가까운 정상 머리색으로 채우고 살짝 블러한다. 영역: 2배 파츠 좌표 x 1000~1400, y 1300~1790(그 아래 어두운 머리 그늘 띠는 원래 그림이라 건드리지 않음)(흔들기 상자 안).
sync_wave_parts 앞에 실행."""
import sys, numpy as np, cv2
from scipy import ndimage
from PIL import Image
d = sys.argv[1]
W = np.array(Image.open(f'{d}/hair_back_wave.png').convert('RGBA')); B = np.array(Image.open(f'{d}/hair_back.png').convert('RGBA'))
x0, x1, y0, y1 = 1000, 1400, 1300, 1790
w = W[y0:y1, x0:x1]; b = B[y0:y1, x0:x1].astype(int); c = w[..., :3].astype(int)
hole = b[..., 3] < 20
bdark = (b[..., 3] > 100) & (b[..., :3].sum(-1) < 400)
near = cv2.dilate(hole.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
band = cv2.dilate((bdark & near).astype(np.uint8), np.ones((17, 17), np.uint8)) > 0
wdark = c.sum(-1) < 330
tgt = band & (w[..., 3] > 0) & ~wdark & ~(~hole & ~bdark & (np.abs(c - b[..., :3]).max(-1) < 12))
hair = (w[..., 3] > 200) & ~wdark & ((c[..., 0] - c[..., 1]) >= 55) & ~(cv2.dilate(band.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
_, (iy, ix) = ndimage.distance_transform_edt(~hair, return_indices=True)
fill = cv2.GaussianBlur(w[..., :3][iy, ix].astype(np.float32), (0, 0), 7)
a_ = cv2.GaussianBlur(tgt.astype(np.float32), (0, 0), 9); a_ = np.maximum(a_ * (~wdark) * (w[..., 3] > 200), tgt)[..., None]
w[..., :3] = (w[..., :3] * (1 - a_) + fill * a_).astype(np.uint8); w[..., 3][tgt] = 255
W[y0:y1, x0:x1] = w; Image.fromarray(W).save(f'{d}/hair_back_wave.png'); print('fixed', int(tgt.sum()))
