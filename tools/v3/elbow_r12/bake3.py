import numpy as np, cv2, json
from PIL import Image
import comp; comp.PP='/workspace/qa11/el/scratch/'
from comp import *
L,M=layers(); base=compose(L)
out=np.load('elb_out.npy'); work=np.load('elb_work.npy')
aall=np.zeros(base.shape[:2],np.float32)
for k in ('hair','bl','bu','fu','hand'): aall=aall+L[k][...,3]*(1-aall)
diff=np.abs(out[...,:3]-base[...,:3]).max(2)>1.5/255
P=cv2.dilate(diff.astype(np.uint8),np.ones((9,9)))>0
P&=work&(aall>0.99)
P=P.astype(np.float32)
pass
ys,xs=np.nonzero(P>0)
# box->part coords: C2 = R(p-P0)+T ; box = C2 - (X0,Y0)
pts=np.stack([xs+X0,ys+Y0],1).astype(np.float64)
pp=(pts-T)@R + P0     # R^T applied: (v)@R == R^T v
print('part bbox',pp.min(0),pp.max(0))
A=np.array(Image.open(PP+'hand_r.png').convert('RGBA')).astype(np.float32)/255
h0,w0=A.shape[:2]
padL,padR,padT,padB=12,0,0,44
NW,NH=w0+padL+padR,h0+padT+padB
B=np.zeros((NH,NW,4),np.float32); B[padT:padT+h0,padL:padL+w0]=A
# warp patch (premultiplied) from box into new part space: part' = R^T(box+X0Y0 - T)+P0+pad
Minv=np.zeros((2,3)); Minv[:,:2]=R.T; Minv[:,2]=R.T@(np.array([X0,Y0])-T)+P0+np.array([padL,padT])
src=np.dstack([out[...,:3]*P[...,None],P])
wp=cv2.warpAffine(src,Minv,(NW,NH),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
a=wp[...,3:4]; col=wp[...,:3]
B=np.concatenate([col+B[...,:3]*B[...,3:4]*(1-a), a+B[...,3:4]*(1-a)],2)
B[...,:3]=B[...,:3]/np.maximum(B[...,3:4],1e-5)
kp=np.load('elb_keep.npy')
kw=cv2.warpAffine(kp,Minv,(NW,NH),flags=cv2.INTER_LINEAR,borderValue=1)
B[...,3]*=kw
Image.fromarray((np.clip(B,0,1)*255+.5).astype(np.uint8)).save('/workspace/ssb/public/v3-demo/parts/hand_r.png')
