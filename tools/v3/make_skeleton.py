"""build.json → skeleton.json (Spine JSON 과 같은 모양: bones/slots/skins/animations; 좌표는 y 아래, 변환 시 y 뒤집기)"""
import json, math, sys, shutil, os
DST=sys.argv[1]; BD=sys.argv[2] if len(sys.argv)>2 else 'out'
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
# 손 흔들기 팔(그림 갈아 끼우기): 소매까지 한 장이라 소매가 늘 팔 뿌리를 위에서 덮는다
order.append(('arm_up_r','arm_up_r',b['wave_body']))
order.append(('hair_front','head',b['hair'][1]))
slots=[];skin={}
for s,bone,a in order:
    sl={'name':s,'bone':bone}
    if s=='eyes': skin[s]={'eyes_closed':att(b['eyes'])}
    elif s=='arm_up_r': skin[s]={a['name']:att(a),**{c['name']:att(c) for c in CS.get('arm_up_r',[])}}; sl['attachment']=a['name']
    elif isinstance(a,list): skin[s]={c['name']:att(c) for c in a}   # 옷 슬롯: 기본은 비어 있음, 옷이 고름
    else: skin[s]={a['name']:att(a),**{c['name']:att(c) for c in CS.get(s,[])}}; sl['attachment']=a['name']
    slots.append(sl)
for f in os.listdir(f'{BD}/parts'): shutil.copy(f'{BD}/parts/{f}',f'{DST}/parts/{f}')
outfits={}
for c in b['cloth']: outfits.setdefault(c['outfit'],{})[c['slot']]=c['name']
anims={'blink':{'period':4.0,'slots':{'eyes':{'attachment':[{'time':0,'name':None},{'time':3.82,'name':'eyes_closed'},{'time':3.95,'name':None}]}}},
 'breathe':{'period':3.2,'bones':{'chest':{'scale':[{'time':0,'y':1},{'time':1.6,'y':1.012},{'time':3.2,'y':1}]},'head':{'translate':[{'time':0,'y':0},{'time':1.6,'y':-1.5},{'time':3.2,'y':0}]}}},
 # 손 흔들기 = 자세 바꾸기(swap) + 어깨 안쪽 축으로 살짝 흔들기(±4°). 팔을 돌려 들지 않으므로 이음새가 안 생긴다.
 'wave':{'period':1.6,'swap':{'on':0.06,'off':1.54,'hide':['upperarm_r','forearm_r','hand_r','sleeve_r'],'show':['arm_up_r']},
   'bones':{'arm_up_r':{'rotate':[{'time':0,'value':0},{'time':0.2,'value':0},{'time':0.45,'value':-4},{'time':0.75,'value':3},{'time':1.05,'value':-4},{'time':1.3,'value':0},{'time':1.6,'value':0}]}}}}
accs=[{'name':a['name'],'path':f"parts/{a['name']}.png",'width':a['w'],'height':a['h']} for a in b['accs']]
json.dump({'skeleton':{'spine':'4.2-like','width':b['size'][0],'height':b['size'][1],'stagePad':80,'note':'y-down; stagePad=무대 좌우 여백(px); Spine 로 옮길 때 y·rotation 부호 반대'},
 'bones':bones,'slots':slots,'skins':[{'name':'default','attachments':skin}],'outfits':outfits,'accessories':accs,'animations':anims},
 open(f'{DST}/skeleton.json','w'),ensure_ascii=False,indent=1)
print('slots',len(slots),'bones',len(bones))
