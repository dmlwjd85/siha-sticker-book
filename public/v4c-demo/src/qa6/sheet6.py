from PIL import Image,ImageDraw,ImageFont
fp='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
F=ImageFont.truetype(fp,28);G=ImageFont.truetype(fp,20)
O=[('none','기본 몸'),('dress','원피스'),('top','세일러'),('crop','크롭 상의')]
Fr=[('wave_000','정지'),('wave_012','손 흔들기 (최대 각도)'),('wave_024','손 흔들기 (반대)'),('idle_060','숨쉬기')]
cw,ch=330,520
S=Image.new('RGB',(160+cw*len(Fr),70+ch*len(O)),(255,255,255));d=ImageDraw.Draw(S)
d.text((10,5),'v4c 재구축 비교 시트',font=F,fill=0)
for j,(f,l) in enumerate(Fr): d.text((170+j*cw,42),l,font=G,fill=0)
for i,(o,l) in enumerate(O):
  d.text((10,70+i*ch+ch//2),l,font=F,fill=0)
  for j,(f,_) in enumerate(Fr):
    im=Image.new('RGB',(1100,1600),(235,235,240));x=Image.open(f'{o}_{f}.png').convert('RGBA');im.paste(x,(0,0),x)
    S.paste(im.crop((180,0,940,1200)).resize((cw-10,ch-10)),(160+j*cw,75+i*ch))
S.save('/workspace/ssb/public/v4c-demo/src/qa6/compare_sheet.png')
Z=[('겨드랑이 wave_012',(385,630,445,720)),('왼어깨 wave_012',(330,560,460,740)),('오른어깨 idle_060',(590,570,680,680))]
rows=[]
for o,l in O:
  for zl,b in Z:
    f=zl.split()[1];im=Image.new('RGB',(1100,1600),(255,0,255));x=Image.open(f'{o}_{f}.png').convert('RGBA');im.paste(x,(0,0),x)
    rows.append((f'{l} · {zl} (400%)',im.crop(b).resize(((b[2]-b[0])*4,(b[3]-b[1])*4),Image.NEAREST)))
W=sum(r[1].width for r in rows[:3])+60;hh=max(r[1].height for r in rows)
H4=ImageFont.truetype(fp,44)
Z4=Image.new("RGB",(W,(hh+80)*4),(255,255,255));d=ImageDraw.Draw(Z4)
for i in range(4):
  x=0
  for t,im in rows[i*3:i*3+3]: d.text((x,i*(hh+80)+4),t,font=H4,fill=0);Z4.paste(im,(x,i*(hh+80)+64));x+=im.width+30
Z4.save('/workspace/ssb/public/v4c-demo/src/qa6/zoom400_sheet.png')
