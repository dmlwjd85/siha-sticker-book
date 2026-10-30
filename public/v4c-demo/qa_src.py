import sys;from PIL import Image
c=sys.argv[1];im=Image.open(f'/workspace/siha-v4/rebuild/body_F_{c}.jpg');s=720/576
B={'neck':(230,230,350,310),'handR':(370,480,460,590),'handL':(110,200,210,300),'armpitL':(150,250,260,420),'armpitR':(310,260,420,420),'waist':(200,370,360,470)}
for n,b in B.items():
  b=tuple(int(v*s) for v in b);x=im.crop(b);x.resize((x.width*4,x.height*4),Image.NEAREST).save(f'/tmp/v4c/{c}_{n}.png')
