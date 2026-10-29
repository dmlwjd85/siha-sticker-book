import numpy as np, cv2
from PIL import Image
from scipy.ndimage import gaussian_filter1d
import comp
from comp import *
PPth=comp.PP
# ---- 1) hair spike: remove in hair_back & hair_back_wave (part coords) ----
L,M=layers(); H,W=L['hair'].shape[:2]
hd=L['hand'][...,3]
for n in ('hair_back','hair_back_wave'):
    A=np.array(Image.open(PPth+n+'.png').convert('RGBA'))
    # box (200..300, 390..452) -> part (box+X0-606, box+Y0-204)
    bx0,bx1,by0,by1=206,300,388,452
    sub=hd[by0:by1,bx0:bx1]<0.995            # outside the forearm
    m=np.zeros(A.shape[:2],bool)
    m[by0+Y0-204:by1+Y0-204, bx0+X0-606:bx1+X0-606]=sub
    A[...,3][m]=0
    Image.fromarray(A).save(PPth+n+'.png')
