import numpy as np
from PIL import Image
for n in ('body_upper','body_upper_wave'):
    A=np.array(Image.open('/workspace/qa11/r13/%s.png'%n))  # backup originals
    H,W=A.shape[:2]; yy,xx=np.mgrid[0:H,0:W]
    m=(yy>1560)&(xx<int(__import__("sys").argv[1]))&(yy<1900)
    A[...,3][m]=0
    Image.fromarray(A).save('/workspace/ssb/public/v3-demo/parts/%s.png'%n)
