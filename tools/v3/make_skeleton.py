"""build.json → skeleton.json (Spine JSON 과 같은 모양: bones/slots/skins/animations; 좌표는 y 아래, 변환 시 y 뒤집기)"""
import json, math, sys, shutil, os
DST=sys.argv[1]; BD=sys.argv[2] if len(sys.argv)>2 else 'out'
WAVE_UP=float(os.environ.get('WAVE_UP','-35')); FORE=float(os.environ.get('WAVE_FORE','-108'))  # 윗팔 최대 각도(이음새 검사로 정함)
b=json.load(open(f'{BD}/build.json'))
bones=[]
J={n:s for n,p,s,e in b['bones']}
for n,p,s,e in b['bones']:
    ps=J[p] if p else (0,0)
    bones.append({'name':n,**({'parent':p} if p else {}),'x':s[0]-ps[0],'y':s[1]-ps[1],
                  'rotation':0,'length':round(math.hypot(e[0]-s[0],e[1]-s[1]),1),'rest':{'x':s[0],'y':s[1]}})
A={a['name']:a for a in b['atts'] if a}
CS={}  # 슬롯 → [옷 조각]
for c in b['cloth']: CS.setdefault(c['slot'],[]).append(c)
def att(a): return {'path':f"parts/{a['name']}.png",'x':a['x'],'y':a['y'],'width':a['w'],'height':a['h']}
BONE_OF={'socks_l':'shin_l','socks_r':'shin_r','shoes_l':'foot_l','shoes_r':'foot_r','bottom':'pelvis','top':'chest','sleeve_l':'upperarm_l','sleeve_r':'upperarm_r'}
def cl(*names): return [(n,BONE_OF[n],CS.get(n,[])) for n in names]
order=[('hair_back','head',b['hair'][0])]
for n in ['thigh_l','thigh_r','shin_l','shin_r','foot_l','foot_r']: order.append((n,n,A[n]))
order+=cl('socks_l','socks_r','shoes_l','shoes_r')
for n in ['pelvis','chest','neck','head']: order.append((n,n,A[n]))
order+=[('eyes','head',None)]
# 윗팔은 윗옷 밑(어깨 이음새·민소매를 옷이 덮음), 소매는 윗팔과 같이 돌고, 아래팔·손은 맨 위
for n in ['upperarm_l','upperarm_r']: order.append((n,n,A[n]))
order+=cl('bottom','top','sleeve_l','sleeve_r')
for n in ['forearm_l','hand_l','forearm_r','hand_r']: order.append((n,n,A[n]))
order.append(('hair_front','head',b['hair'][1]))
slots=[];skin={}
for s,bone,a in order:
    sl={'name':s,'bone':bone}
    if s=='eyes': skin[s]={'eyes_closed':att(b['eyes'])}
    elif isinstance(a,list): skin[s]={c['name']:att(c) for c in a}   # 옷 슬롯: 기본은 비어 있음, 옷이 고름
    else: skin[s]={a['name']:att(a)}; sl['attachment']=a['name']
    slots.append(sl)
for f in os.listdir(f'{BD}/parts'): shutil.copy(f'{BD}/parts/{f}',f'{DST}/parts/{f}')
outfits={}
for c in b['cloth']: outfits.setdefault(c['outfit'],{})[c['slot']]=c['name']
anims={'blink':{'period':4.0,'slots':{'eyes':{'attachment':[{'time':0,'name':None},{'time':3.82,'name':'eyes_closed'},{'time':3.95,'name':None}]}}},
 'breathe':{'period':3.2,'bones':{'chest':{'scale':[{'time':0,'y':1},{'time':1.6,'y':1.012},{'time':3.2,'y':1}]},'head':{'translate':[{'time':0,'y':0},{'time':1.6,'y':-1.5},{'time':3.2,'y':0}]}}},
 'wave':{'period':1.6,'bones':{'upperarm_r':{'rotate':[{'time':0,'value':0},{'time':0.25,'value':0},{'time':0.5,'value':WAVE_UP},{'time':1.15,'value':WAVE_UP},{'time':1.4,'value':0},{'time':1.6,'value':0}]},
   'forearm_r':{'rotate':[{'time':0,'value':0},{'time':0.25,'value':FORE},{'time':0.6,'value':FORE-22},{'time':0.8,'value':FORE},{'time':1.0,'value':FORE-22},{'time':1.15,'value':FORE},{'time':1.4,'value':FORE},{'time':1.6,'value':0}]}}}}
accs=[{'name':a['name'],'path':f"parts/{a['name']}.png",'width':a['w'],'height':a['h']} for a in b['accs']]
json.dump({'skeleton':{'spine':'4.2-like','width':b['size'][0],'height':b['size'][1],'stagePad':80,'note':'y-down; stagePad=무대 좌우 여백(px); Spine 로 옮길 때 y·rotation 부호 반대'},
 'bones':bones,'slots':slots,'skins':[{'name':'default','attachments':skin}],'outfits':outfits,'accessories':accs,'animations':anims},
 open(f'{DST}/skeleton.json','w'),ensure_ascii=False,indent=1)
print('slots',len(slots),'bones',len(bones))
