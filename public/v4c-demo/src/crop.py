import sys
from PIL import Image
c,k,x0,y0,x1,y1=sys.argv[1],sys.argv[2],*map(int,sys.argv[3:7])
D='public/v4c-demo/src'
im=Image.open(f'{D}/body_F_{c}.jpg').convert('RGB');s=im.size[0]/576
im.crop((int(x0*s),int(y0*s),int(x1*s),int(y1*s))).resize(((x1-x0)*4,(y1-y0)*4),Image.NEAREST).save(f'{D}/crops/{c}_{k}.png')
