import numpy as np, cv2, json
from PIL import Image
from comp import *
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
sd=d_out-d_in
OL=np.array([0.357,0.212,0.275])
a=np.clip(1-np.abs(sd+3.2)/3.9,0,1)   # ~6px line straddling inside
a=np.clip(a*1.6,0,1)
band=(np.abs(sd)<9)&work
c[band]=c[band]*(1-a[band,None])+OL*a[band,None]
# outside union inside work: the old outer lines of the stub/gap that are now outside -> leave as is (hair)
# crook crease: short line at the inner corner
out=base.copy(); out[...,:3]=np.where(work[...,None],c,base[...,:3])
save(out,'after_box.png')
np.save('elb_out.npy',out); np.save('elb_work.npy',work)
print('work',work.sum(),'U0',U0.sum(),'inner&work',(inner&work).sum(),'bad',bad.sum(),'band',band.sum(),'fu>.05',(fu>.05).sum())
v=base[...,:3]*.4
v[...,0]+=(hd>.5)*.4; v[...,1]+=((bu>.5)&armzone)*.4; v[...,2]+=bad*.6
v[(U>0)&(U0==0)]=[1,1,0]
v[~work]*=.5
Image.fromarray((np.clip(v,0,1)*255).astype(np.uint8)).crop((150,250,650,650)).save('dbg.png')
v=out[...,:3].copy(); v[~work]*=.4
Image.fromarray((np.clip(v,0,1)*255).astype(np.uint8)).crop((150,250,650,650)).save('dbg2.png')
