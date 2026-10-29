import numpy as np, cv2, json
from PIL import Image
from comp import *
L,M=layers(); base=compose(L)
out=np.load('elb_out.npy'); work=np.load('elb_work.npy')
aall=np.zeros(base.shape[:2],np.float32)
for k in ('hair','bl','bu','fu','hand'): aall=aall+L[k][...,3]*(1-aall)
diff=np.abs(out[...,:3]-base[...,:3]).max(2)>1.5/255
P=cv2.dilate(diff.astype(np.uint8),np.ones((5,5)))>0
P&=work&(aall>0.99)
P=P.astype(np.float32)
P=cv2.GaussianBlur(P,(0,0),0.7)*P  # soft but no spill
ys,xs=np.nonzero(P>0)
# box->part coords: C2 = R(p-P0)+T ; box = C2 - (X0,Y0)
pts=np.stack([xs+X0,ys+Y0],1).astype(np.float64)
pp=(pts-T)@R + P0     # R^T applied: (v)@R == R^T v
print('part bbox',pp.min(0),pp.max(0))
A=np.array(Image.open(PP+'hand_r.png').convert('RGBA')).astype(np.float32)/255
h0,w0=A.shape[:2]
padL=int(max(0,-np.floor(pp[:,0].min()))+8); padR=int(max(0,np.ceil(pp[:,0].max())-w0+1)+8)
padT=int(max(0,-np.floor(pp[:,1].min()))+8); padB=int(max(0,np.ceil(pp[:,1].max())-h0+1)+8)
padL+=padL%2; padR+=padR%2; padT+=padT%2; padB+=padB%2
if pp[:,0].min()>=0: padL=0
if pp[:,0].max()<w0: padR=0
if pp[:,1].min()>=0: padT=0
if pp[:,1].max()<h0: padB=0
print('pads',padL,padR,padT,padB)
NW,NH=w0+padL+padR,h0+padT+padB
B=np.zeros((NH,NW,4),np.float32); B[padT:padT+h0,padL:padL+w0]=A
# warp patch (premultiplied) from box into new part space: part' = R^T(box+X0Y0 - T)+P0+pad
Minv=np.zeros((2,3)); Minv[:,:2]=R.T; Minv[:,2]=R.T@(np.array([X0,Y0])-T)+P0+np.array([padL,padT])
src=np.dstack([out[...,:3]*P[...,None],P])
wp=cv2.warpAffine(src,Minv,(NW,NH),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
a=wp[...,3:4]; col=wp[...,:3]
B=np.concatenate([col+B[...,:3]*B[...,3:4]*(1-a), a+B[...,3:4]*(1-a)],2)
B[...,:3]=B[...,:3]/np.maximum(B[...,3:4],1e-5)
Image.fromarray((np.clip(B,0,1)*255+.5).astype(np.uint8)).save(PP+'hand_r.png')
sk='/workspace/ssb/public/v3-demo/skeleton.json'; S=open(sk).read()
old='"path": "parts/hand_r.png",\n            "x": 389,\n            "y": 549,\n            "width": 186,\n            "height": 465'
new=f'"path": "parts/hand_r.png",\n            "x": {389-padL//2},\n            "y": {549-padT//2},\n            "width": {NW//2},\n            "height": {NH//2}'
assert old in S; open(sk,'w').write(S.replace(old,new)); print(new)
