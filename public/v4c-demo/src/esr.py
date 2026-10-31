# 4단계: Real-ESRGAN x4 (anime_6B) → 0.5배 LANCZOS 다운스케일 = 2배 원본
import sys,torch,numpy as np
from PIL import Image
from spandrel import ModelLoader
m=ModelLoader().load_from_file('/workspace/esr/RealESRGAN_x4plus_anime_6B.pth').model.eval()
torch.set_num_threads(8)
for f in sys.argv[1:]:
    im=Image.open(f).convert('RGB');a=torch.from_numpy(np.asarray(im)).permute(2,0,1)[None].float()/255
    T=256;P=16;_,_,H,W=a.shape;o=torch.zeros(1,3,H*4,W*4)
    with torch.no_grad():
        for y in range(0,H,T):
            for x in range(0,W,T):
                y0,x0=max(0,y-P),max(0,x-P);y1,x1=min(H,y+T+P),min(W,x+T+P)
                r=m(a[:,:,y0:y1,x0:x1]).clamp(0,1)
                o[:,:,y*4:min(H,y+T)*4,x*4:min(W,x+T)*4]=r[:,:,(y-y0)*4:(y-y0+min(H,y+T)-y)*4,(x-x0)*4:(x-x0+min(W,x+T)-x)*4]
    up=Image.fromarray((o[0].permute(1,2,0).numpy()*255).round().astype(np.uint8))
    up.resize((W*2,H*2),Image.LANCZOS).save('x4/'+f.rsplit('/',1)[-1].rsplit('.',1)[0]+'_x2.png');print(f,flush=True)
