from PIL import Image, ImageDraw
D='docs/v3/qa/v3-review16/'
B='/workspace/qa11/r12a_'; A='/workspace/qa11/r13/h2_'
def L(p):
    im=Image.open(p).convert('RGBA'); bg=Image.new('RGBA',im.size,'white'); bg.alpha_composite(im); return bg.convert('RGB')
for m in ('none_idle','basic_idle','none_wave15','basic_wave15'):
    b=L(B+m+'.png'); a=L(A+m+'.png')
    w,h=b.size; s=Image.new('RGB',(w*2,h),'white'); s.paste(b,(0,0)); s.paste(a,(w,0)); s.save(D+'100_before_after_%s.png'%m)
    box=(230,380,530,680)
    s=Image.new('RGB',(2400,1200),'white'); s.paste(b.crop(box).resize((1200,1200),Image.LANCZOS),(0,0)); s.paste(a.crop(box).resize((1200,1200),Image.LANCZOS),(1200,0)); s.save(D+'400_before_after_%s.png'%m)
def diag(im,fore,up,J,lab):
    im=im.crop((230,380,530,680)).resize((1200,1200),Image.LANCZOS); d=ImageDraw.Draw(im)
    T=lambda x,y:((x-230)*4,(y-380)*4)
    for f,c in ((fore,'blue'),(up,'red')): d.line([T(f(y),y) for y in (380,720)],fill=c,width=5)
    d.ellipse([T(*J)[0]-14,T(*J)[1]-14,T(*J)[0]+14,T(*J)[1]+14],outline='lime',width=5)
    d.text((20,20),lab,fill='black'); return im
b=diag(L(B+'none_idle.png'),lambda y:273.5+0.42*(y-400),lambda y:434.5-0.144*(y-480),(402,706),'before: elbow offset 56-60px, axes cross (402,706) 80-100px below elbow, 31deg')
a=diag(L(A+'none_idle.png'),lambda y:360+0.26*(y-440),lambda y:435-0.144*(y-440),(411,636),'after: elbow offset ~10px, axes cross at elbow')
s=Image.new('RGB',(2400,1200),'white'); s.paste(b,(0,0)); s.paste(a,(1200,0)); s.save(D+'diag_axes_before_after.png')
