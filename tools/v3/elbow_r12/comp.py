import numpy as np, cv2
from PIL import Image
PP='/workspace/ssb/public/v3-demo/parts/'
X0,Y0,X1,Y1=400,1400,1300,2300
th=np.deg2rad(-34); R=np.array([[np.cos(th),-np.sin(th)],[np.sin(th),np.cos(th)]])
T=np.array([812.8,2006.4]); P0=np.array([20,900])
def load(n): return np.array(Image.open(PP+n+'.png').convert('RGBA')).astype(np.float32)/255
def place(n, off):
    a=load(n); H,W=Y1-Y0,X1-X0; out=np.zeros((H,W,4),np.float32)
    ox,oy=off[0]-X0,off[1]-Y0
    ys0,xs0=max(0,oy),max(0,ox); ys1,xs1=min(H,oy+a.shape[0]),min(W,ox+a.shape[1])
    if ys1>ys0 and xs1>xs0: out[ys0:ys1,xs0:xs1]=a[ys0-oy:ys1-oy,xs0-ox:xs1-ox]
    return out
def hand(a=None):
    if a is None: a=load('hand_r')
    # C2 = R(p-P0)+T  -> p = R^T(C2-T)+P0 ; build affine for warp from part to box
    M=np.zeros((2,3)); M[:,:2]=R; M[:,2]=T-R@P0-np.array([X0,Y0])
    return cv2.warpAffine(a,M,(X1-X0,Y1-Y0),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0)), M
def over(dst,src):
    a=src[...,3:4]; return np.concatenate([src[...,:3]*a+dst[...,:3]*(1-a), a+dst[...,3:4]*(1-a)],2)
def layers(outfit=True):
    L={'hair':place('hair_back',(606,204)),'bu':place('body_upper',(778,242)),'bl':place('body_lower',(924,2560))}
    if outfit: L['fu']=place('basic_upper',(956,1356))
    L['hand'],M=hand(); return L,M
def compose(L,order=('hair','bl','bu','fu','hand')):
    c=np.zeros_like(L['hair']); c[...,:3]=0.08; c[...,3]=1
    for k in order:
        if k in L: c=over(c,L[k])
    return c
def save(a,f,k=1):
    im=Image.fromarray((np.clip(a[...,:3],0,1)*255).astype(np.uint8))
    if k!=1: im=im.resize((im.width*k//2,im.height*k//2),Image.LANCZOS)
    im.save(f)
