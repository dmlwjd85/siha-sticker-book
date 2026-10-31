from PIL import Image,ImageDraw,ImageFont
fp='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc';H=ImageFont.truetype(fp,40)
Q=[('dress','wave_000','치맛단',(330,1060,530,1220)),('dress','wave_012','치맛단',(330,1060,530,1220)),('dress','idle_060','치맛단',(330,1060,530,1220)),
('dress','wave_000','요술봉',(760,700,900,1000)),('dress','wave_012','요술봉',(760,700,900,1000)),('dress','wave_000','티아라',(430,130,650,260)),
('none','wave_012','겨드랑이',(385,630,445,720)),('dress','wave_012','엄지',(300,455,390,545)),('dress','wave_012','소매',(340,600,480,720)),
('top','wave_012','소매단',(340,600,480,720)),('crop','wave_012','소매단',(340,600,480,720)),('crop','wave_000','크롭 c27e 밑단',(330,800,700,960))]
ims=[]
for o,f,l,b in Q:
  im=Image.new('RGB',(1100,1600),(255,0,255));x=Image.open(f'{o}_{f}.png').convert('RGBA');im.paste(x,(0,0),x)
  ims.append((f'{o} {f} {l}',im.crop(b).resize(((b[2]-b[0])*4,(b[3]-b[1])*4),Image.NEAREST)))
cols=3;import math;rows=math.ceil(len(ims)/cols)
cw=max(i.width for _,i in ims)+30;rh=max(i.height for _,i in ims)+70
S=Image.new('RGB',(cw*cols,rh*rows),(255,255,255));d=ImageDraw.Draw(S)
for k,(t,i) in enumerate(ims):
  x,y=(k%cols)*cw,(k//cols)*rh;d.text((x,y),t,font=H,fill=0);S.paste(i,(x,y+60))
S.save('/workspace/ssb/public/v4c-demo/src/qa7/zoom400_qa7.png');print(S.size)
