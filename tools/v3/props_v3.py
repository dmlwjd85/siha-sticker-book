from build_v3 import *
rgb,al=load('mic.jpg',False); m=hires(rgb,al,[])
ys,xs=np.where(m[...,3]>0); m=m[ys.min():ys.max()+1,xs.min():xs.max()+1]
FULL_H=m.shape[0]; m=m[:int(FULL_H*0.6)]   # 손잡이 아래쪽은 주먹 안에서 끝냄(손 밖으로 삐져나오지 않게). 원래 길이는 skeleton 에서 grip 계산에 씀
json.dump({'full_h':FULL_H},open(f'{OUT}/mic_meta.json','w'))
Image.fromarray(m).save(f'{OUT}/parts/prop_mic.png',optimize=True); print(m.shape)
# 장식 두 개(리본·별 핀): 한 장에서 덩어리 둘로 나눔
im=Image.open(f'{RAW}/accs.jpg').convert('RGB'); tp=f'{TMP}/accs.png'; im.save(tp)
rgb=np.array(im).astype(np.float32); a=rmbg(tp).astype(np.float32)[...,3]/255
bgc=np.median(rgb[:8].reshape(-1,3),0); a[ndimage.binary_opening(np.abs(rgb-bgc).max(-1)<10,iterations=2)]=0
h=hires(rgb,a,[]); lb,n=ndimage.label(h[...,3]>20); sz=ndimage.sum(np.ones(lb.shape),lb,range(1,n+1)); big=np.argsort(sz)[::-1][:2]+1
cs=sorted([ndimage.find_objects((lb==i).astype(int))[0] for i in big],key=lambda s:s[1].start)
for nm,sl in zip(['acc_ribbon','acc_star'],cs):
    m=h[sl].copy(); m[...,3]=(m[...,3]*(ndimage.binary_dilation(lb[sl]>0,iterations=3))).astype(np.uint8); Image.fromarray(m).save(f'{OUT}/parts/{nm}.png',optimize=True); print(nm,m.shape)
