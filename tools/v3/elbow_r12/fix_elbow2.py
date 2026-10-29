import numpy as np, cv2, json
from PIL import Image
import comp; comp.PP='/workspace/qa11/el/scratch/'
from comp import *
from scipy.ndimage import gaussian_filter1d
L,M=layers(outfit=True)
H,W=L['hair'].shape[:2]
base=compose(L)            # current look (basic)
hd=L['hand'][...,3]; bu=L['bu'][...,3]; fu=L['fu'][...,3]
yy,xx=np.mgrid[0:H,0:W]
# arm part of body_upper only: left of torso line (box coords), rows of elbow
armzone=(xx<760)&(yy>300)
U0=((hd>.1)|((bu>.5)&armzone)).astype(np.uint8)
k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(21,21))
U=cv2.morphologyEx(U0,cv2.MORPH_CLOSE,k)
U=cv2.GaussianBlur(U.astype(np.float32),(0,0),5)>.5
U=U.astype(np.uint8)
cs,_=cv2.findContours(U,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
cn=max(cs,key=len)[:,0,:].astype(np.float64)
def wt(p):
    x,y=p[:,0],p[:,1]
    e=np.clip((1-(((x-470)/190.)**2+((y-575)/115.)**2))*4,0,1)
    k=np.clip(np.maximum((480-x)/15,(y-530)/15),0,1)
    return e*k
w=wt(cn)
sm=np.stack([gaussian_filter1d(gaussian_filter1d(cn[:,i],10,mode='wrap'),6,mode='wrap') for i in (0,1)],1)
cn2=cn*(1-w[:,None])+sm*w[:,None]
big=np.zeros((H*4,W*4),np.uint8); cv2.fillPoly(big,[np.round(cn2*4+1.5).astype(np.int32)],1)
sdb=cv2.distanceTransform(1-big,cv2.DIST_L2,5)-cv2.distanceTransform(big,cv2.DIST_L2,5)
SD=cv2.resize(sdb,(W,H),interpolation=cv2.INTER_AREA)/4
U=(SD<0).astype(np.uint8)
# working area: around the elbow, away from shirt
work=(yy>380)&(yy<660)&(xx>200)&(xx<640)
work=work&(cv2.dilate((fu>.05).astype(np.uint8),np.ones((9,9)))==0)
c=base[...,:3].copy()
dark=c.sum(2)<1.4
# skin colour sample & refill interior (kill inner outlines + gap)
inner=cv2.erode(U,np.ones((15,15)))>0
bad=inner&work&(dark|( (L['hair'][...,3]>.5)&(hd<.5)&(bu<.5) ))
bad=cv2.dilate((bad|((hd>.02)&(hd<.98)&(bu>.5))).astype(np.uint8),np.ones((9,9)))>0
bad&=inner
bad|=(dark&work&(cv2.distanceTransform(U,cv2.DIST_L2,5)>7))
good=inner&~bad&work|(inner&~work)
def refill(img,bad,good,s=9):
    g=good.astype(np.float32); out=img.copy()
    num=cv2.GaussianBlur(img*g[...,None],(0,0),s); den=cv2.GaussianBlur(g,(0,0),s)[...,None]
    out[bad]=(num/np.maximum(den,1e-4))[bad]; return out
core=bad|(((U>0)&(U0==0))&work)
dz=cv2.distanceTransform((~core).astype(np.uint8),cv2.DIST_L2,5)
zf=np.clip((60-dz)/25,0,1)
d_in0=cv2.distanceTransform(U,cv2.DIST_L2,5)
rim=(d_in0>0)&(d_in0<11)&work&(((xx-470)/150.)**2+((yy-580)/90.)**2<1)
bad|=rim
good&=~rim
c=refill(c,bad,good,9)
# new skin area of closed union that was not skin (gap) outside inner as well
newskin=(U>0)&~(U0>0)&work
c=refill(c,newskin&~inner,inner&~bad,7) if (newskin&~inner).any() else c
# single outline: SDF band on union boundary
d_in=cv2.distanceTransform(U,cv2.DIST_L2,5); d_out=cv2.distanceTransform(1-U,cv2.DIST_L2,5)
sd=SD
OL=np.array([0.357,0.212,0.275])
LW=6.5
rb=work&(sd>-LW-4)&(sd<0.5)
g2=(work&(sd<-LW-5)&(sd>-30)&~dark&(c.sum(2)>2.3)).astype(np.float32)
num=cv2.GaussianBlur(c*g2[...,None],(0,0),4); den=cv2.GaussianBlur(g2,(0,0),4)
rb&=den>0.15
c[rb]=(num/np.maximum(den,1e-4)[...,None])[rb]
ref=cv2.medianBlur((np.clip(c,0,1)*255).astype(np.uint8),9).astype(np.float32)/255
gz=work&(sd<-LW-1.5)&(xx>380)&(yy>450)&(xx<640)&~(c.sum(2)<1.4)
gh=gz&(np.abs(c-ref).max(2)>1.2/255)
gh=cv2.dilate(gh.astype(np.uint8),np.ones((3,3)))>0
gh&=gz
c[gh]=ref[gh]
print('ghost px',gh.sum())
keep=np.ones((H,W),np.float32)
lz=work&(xx<335)&(yy<480)
keep[lz]=np.clip(1.0-sd[lz],0,1)
np.save('elb_keep.npy',keep)
a=np.clip(np.minimum(sd+LW+0.5,0.5-sd),0,1)
band=(np.abs(sd)<9)&work
c[band]=c[band]*(1-a[band,None])+OL*a[band,None]
# outside union inside work: the old outer lines of the stub/gap that are now outside -> leave as is (hair)
# crook crease: short line at the inner corner
out=base.copy(); out[...,:3]=np.where(work[...,None],c,base[...,:3])
save(out,'after_box.png')
np.save('elb_out.npy',out); np.save('elb_work.npy',work)
