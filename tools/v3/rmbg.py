import numpy as np, sys
from PIL import Image
from scipy import ndimage
def rmbg(path, tol=14):
    im=np.array(Image.open(path).convert('RGB')).astype(np.float32)
    bg=np.median(np.r_[im[:8].reshape(-1,3),im[-8:].reshape(-1,3),im[:,:8].reshape(-1,3),im[:,-8:].reshape(-1,3)],0)
    d=np.abs(im-bg).max(-1)
    lab,_=ndimage.label(d<tol); edge=set(np.unique(np.r_[lab[0],lab[-1],lab[:,0],lab[:,-1]]))-{0}
    fg=~np.isin(lab,list(edge)); fg=ndimage.binary_opening(fg,iterations=1)
    lab2,n=ndimage.label(fg)
    if n>1:
        sz=ndimage.sum(fg,lab2,range(1,n+1)); keep=[i+1 for i,s in enumerate(sz) if s>0.002*fg.size]; fg=np.isin(lab2,keep)
    fg=ndimage.binary_fill_holes(fg)
    dist=ndimage.distance_transform_edt(fg)
    a=np.where(dist>=2,1.0,np.clip(d/60,0,1))*fg
    rgb=np.where(((a>0)&(a<1))[...,None],np.clip((im-(1-a[...,None])*bg)/np.maximum(a[...,None],1e-3),0,255),im)
    return np.dstack([rgb,a*255]).astype(np.uint8)
def crop(a):
    ys,xs=np.where(a[...,3]>128); return a[ys.min():ys.max()+1,xs.min():xs.max()+1]
if __name__=='__main__':
    Image.fromarray(crop(rmbg(sys.argv[1]))).save(sys.argv[2])
