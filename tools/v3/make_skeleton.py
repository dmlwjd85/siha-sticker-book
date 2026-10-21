"""build.json → skeleton.json (Spine JSON 과 같은 모양: bones/slots/skins/animations; 좌표는 y 아래, 변환 시 y 뒤집기)"""
import json, math, sys, shutil, os
b=json.load(open('out/build.json')); DST=sys.argv[1]
bones=[]
J={n:s for n,p,s,e in b['bones']}
for n,p,s,e in b['bones']:
    ps=J[p] if p else (0,0)
    bones.append({'name':n,**({'parent':p} if p else {}),'x':s[0]-ps[0],'y':s[1]-ps[1],
                  'rotation':0,'length':round(math.hypot(e[0]-s[0],e[1]-s[1]),1),'rest':{'x':s[0],'y':s[1]}})
A={a['name']:a for a in b['atts'] if a}; C={c['name']:c for c in b['cloth']}
def att(a): return {'path':f"parts/{a['name']}.png",'x':a['x'],'y':a['y'],'width':a['w'],'height':a['h']}
order=[('hair_back','head',b['hair'][0])]
for n in ['thigh_l','thigh_r','shin_l','shin_r','foot_l','foot_r']: order.append((n,n,A[n]))
for n in ['shin_l','shin_r']: order.append((f'socks_{n[-1]}',n,C[f'outfit_socks_{n}']))
for n in ['foot_l','foot_r']: order.append((f'shoes_{n[-1]}',n,C[f'outfit_shoes_{n}']))
for n in ['pelvis','chest','neck','head']: order.append((n,n,A[n]))
order+=[('eyes','head',None),('bottom','pelvis',C['outfit_bottom_pelvis']),('top','chest',C['outfit_top_chest'])]
for n in ['upperarm_l','forearm_l','hand_l','upperarm_r','forearm_r','hand_r']: order.append((n,n,A[n]))
order+=[('sleeve_l','upperarm_l',C['outfit_sleeve_upperarm_l']),('sleeve_r','upperarm_r',C['outfit_sleeve_upperarm_r'])]
order.append(('hair_front','head',b['hair'][1]))
slots=[];skin={}
for s,bone,a in order:
    sl={'name':s,'bone':bone}
    if s=='eyes': skin[s]={'eyes_closed':att(b['eyes'])}
    else:
        skin[s]={a['name']:att(a)}
        if s not in('top','bottom') and not s.startswith(('socks','shoes','sleeve')): sl['attachment']=a['name']
    slots.append(sl)
for f in os.listdir('out/parts'): shutil.copy(f'out/parts/{f}',f'{DST}/parts/{f}')
outfits={'basic':{'top':'outfit_top_chest','bottom':'outfit_bottom_pelvis','socks_l':'outfit_socks_shin_l','socks_r':'outfit_socks_shin_r','shoes_l':'outfit_shoes_foot_l','shoes_r':'outfit_shoes_foot_r','sleeve_l':'outfit_sleeve_upperarm_l','sleeve_r':'outfit_sleeve_upperarm_r'}}
anims={'blink':{'period':4.0,'slots':{'eyes':{'attachment':[{'time':0,'name':None},{'time':3.82,'name':'eyes_closed'},{'time':3.95,'name':None}]}}},
 'breathe':{'period':3.2,'bones':{'chest':{'scale':[{'time':0,'y':1},{'time':1.6,'y':1.012},{'time':3.2,'y':1}]},'head':{'translate':[{'time':0,'y':0},{'time':1.6,'y':-1.5},{'time':3.2,'y':0}]}}},
 'wave':{'period':1.6,'bones':{'upperarm_r':{'rotate':[{'time':0,'value':0},{'time':0.4,'value':-75},{'time':1.2,'value':-75},{'time':1.6,'value':0}]},
   'forearm_r':{'rotate':[{'time':0,'value':0},{'time':0.4,'value':-40},{'time':0.6,'value':-15},{'time':0.8,'value':-40},{'time':1.0,'value':-15},{'time':1.2,'value':-40},{'time':1.6,'value':0}]}}}}
accs=[{'name':a['name'],'path':f"parts/{a['name']}.png",'width':a['w'],'height':a['h']} for a in b['accs']]
json.dump({'skeleton':{'spine':'4.2-like','width':b['size'][0],'height':b['size'][1],'note':'y-down; Spine 로 옮길 때 y·rotation 부호 반대'},
 'bones':bones,'slots':slots,'skins':[{'name':'default','attachments':skin}],'outfits':outfits,'accessories':accs,'animations':anims},
 open(f'{DST}/skeleton.json','w'),ensure_ascii=False,indent=1)
print('slots',len(slots),'bones',len(bones))
